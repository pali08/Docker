#!/usr/bin/env python3
import numpy as np
import os
from read_bcr_python import read_bcr_bin
from pdb_bins import pdb_rots_to_bins
from draw_plot import draw_points
import cv2
import sys

def find_highest_point(matrix_gethighest):
    prot_array = matrix_gethighest
    matrix_gethighest = np.array(matrix_gethighest) # create numpy array
    max_value = np.amax(matrix_gethighest) # find highest point in topography
    index_of_max_val = np.argmax(matrix_gethighest) # find index of highest point (one value index -in  matrix of size 4x3  [2,0] is 6, [3,1] is 10 etc.- indexing from 0 )
    array_shape = matrix_gethighest.shape # get shape of array
    indices_of_max_value = np.unravel_index(index_of_max_val, array_shape) # get index of highest value in 2D matrix from 1num index to 2num index 
    return(array_shape, prot_array, indices_of_max_value, max_value)

def check_surrounding(matrix):
    matrix_shape, matrix, ind_max_value, max_value = find_highest_point(matrix)
    circ_diameter = 5 # is treshold- should play around and set good value
    x_max = ind_max_value[0]
    y_max = ind_max_value[1]
    warning_was_writen = False
    max_dist = 5.0
    for i in range(0, matrix_shape[0]):
        for j in range(0, matrix_shape[1]): #iterate trough all bcr_array
            if (np.sqrt(((x_max-i)**2)+((y_max-j)**2)) < max_dist): # if value is in circle, do not check it
                continue
            elif(matrix[i][j] < matrix[x_max][y_max] - 1.0 ): # 1.0 is treshold- should play around and set good value, 
                continue #value not in circle but has treshold lesser than we are looking for
            else: # to write warning only once
                return 1
    return 0

#uprav navratovu hodnotu

def opencv_align(bcr_array,pdb_array):

    #print(bcr_array)
    #print(pdb_array)
    bcr = bcr_array.astype(np.float32)
    bcr2 = bcr.copy()
    template = pdb_array.astype(np.float32)
    w, h = template.shape[::-1]

    bcr = bcr2.copy()

    # Apply template Matching
    res = cv2.matchTemplate(bcr,template,1)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

    top_left = min_loc
    bottom_right = (top_left[0] + w, top_left[1] + h)

    #print(top_left)
    #print(bottom_right)

    return(top_left)

def align_matrices(coor_list, bcr_header, bcr_array, rots_count, rots_count_around_z, refine, ref_angle, docker_rough_output, ref_line_num):
    pdb_matrices, list_of_all_rots, list_of_axisangles, list_of_all_angles_z = pdb_rots_to_bins(coor_list, bcr_header, rots_count, rots_count_around_z, refine, ref_angle, docker_rough_output, ref_line_num)

    print(len(pdb_matrices))


    #next section just checks if it aligns to highest point
    index_of_max_val = np.argmax(bcr_array) # find index of highest point (one value index -in  matrix of size 4x3  [2,0] is 6, [3,1] is 10 etc.- indexing from 0 )
    array_shape = bcr_array.shape # get shape of array
    indices_of_max_value = np.unravel_index(index_of_max_val, array_shape) # get index of highest value in 2D matrix from 1num index to 2num index 
    print(indices_of_max_value)
    #end of section

    bcr_array = np.array(bcr_array)
    bcr_array_shape = bcr_array.shape
    max_val_bcr = np.amax(bcr_array) # find highest point in topography
    #print(bcr_array)
    aligned_matrices = []
    korel_sums = []
    matrices_of_diffs = []
    #print(pdb_matrices)
    if (check_surrounding(bcr_array) == 1):
        print("Structure has more highest points- results can be distorted")
    print("Aligning pdb matrices to bcr.")
    for k in range(0,len(pdb_matrices)): #iterate trough list of matrices 

        pdb_array = np.array(pdb_matrices[k])
        pdb_array_shape = pdb_array.shape
        max_val_pdb = np.amax(pdb_array)

        max_val = max_val_bcr - max_val_pdb
        kor_sum = 0
        #print(bcr_array_shape)
        #print(pdb_array_shape)
        try:
            y_dist, x_dist = opencv_align(bcr_array, pdb_array)
        except cv2.error as e:
            print("Cv2 error")
            continue
        new_pdb_array = np.zeros((bcr_array_shape[0],bcr_array_shape[1])) #new pdb array with shape of bcr array 
        diff_matrix = np.copy(new_pdb_array)
        try:
            for i in range(0, pdb_array_shape[0]):
                for j in range(0, pdb_array_shape[1]):
                    #if(i+x_dist >= 0 and j+y_dist >= 0):
                    new_pdb_array[i+x_dist][j+y_dist] = pdb_array[i][j]
                    #else:
                    #raise IndexError("")
            #print(new_pdb_array)
        except IndexError:
            print("Index error")
            continue
        new_pdb_array = new_pdb_array + max_val

        #next section just checks if it aligns to highest point
        index_of_max_val = np.argmax(new_pdb_array) # find index of highest point (one value index -in  matrix of size 4x3  [2,0] is 6, [3,1] is 10 etc.- indexing from 0 )
        array_shape = new_pdb_array.shape # get shape of array
        indices_of_max_value = np.unravel_index(index_of_max_val, array_shape) # get index of highest value in 2D matrix from 1num index to 2num index 
        print(indices_of_max_value)
        #end of section

        aligned_matrices.append(new_pdb_array)
        for i in range(0, bcr_array_shape[0]):
            for j in range(0, bcr_array_shape[1]):
                kor_sum = kor_sum + abs(bcr_array[i][j] - new_pdb_array[i][j])
                diff_matrix[i][j] = abs(bcr_array[i][j] - new_pdb_array[i][j])
        #print(kor_sum)
        #print(new_pdb_array)
        korel_sums.append(kor_sum)
        matrices_of_diffs.append(diff_matrix)
    return(list_of_axisangles, korel_sums, matrices_of_diffs, aligned_matrices, list_of_all_angles_z)

