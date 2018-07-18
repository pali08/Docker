#/usr/bin/env python3
import sys, os
from align_matrices import align_matrices
from read_bcr_python import read_bcr_header, read_bcr_bin
from read_pdb import read_pdb
#from create_folders import create_folder, create_subfolders
import numpy as np
from draw_plot import draw_points
import heapq
from create_folders import CreateFolder
from create_folders import CreateFolderRefine
import transform_coordinates
import linecache
import pathlib



class CompareAndOutput(object):
    def __init__(self, infilenames_pdb, infilenames_bcr, rots_count, rots_count_around_z, best_fits_count,project_name, autorefine, how_much_best, rots_count_glob_ref,rots_count_z_ref,\
                 docker_rough_output, ref_line_num,  corner_background,up_down_steps_count, scale,refine, rmsd, gauss_sigma, boxcar_size):
        self.infilenames_pdb = infilenames_pdb
        self.infilenames_bcr = infilenames_bcr
        self.rots_count = rots_count
        self.rots_count_around_z = rots_count_around_z
        self.best_fits_count = best_fits_count
        self.project_name = project_name
        self.autorefine = autorefine
        self.how_much_best = how_much_best
        self.rots_count_glob_ref = rots_count_glob_ref
        self.rots_count_z_ref = rots_count_z_ref 
        self.ref_line_num = ref_line_num
        self.up_down_steps_count = up_down_steps_count
        self.corner_background = corner_background
        self.scale = scale
        self.rmsd = rmsd
        self.gauss_sigma = gauss_sigma
        self.boxcar_size = boxcar_size
# continue here- now it should be enough to align matrices once more after all procedures (for thispurpose, put all stuff after align matrices into 1 fcia) 
    def compare_and_output(self, infilename_pdb, infilename_bcr):
        self.infilename_pdb = infilename_pdb
        self.infilename_bcr = infilename_bcr
        bcr_array = np.array(read_bcr_bin(self.infilename_bcr))
        bcr_header = read_bcr_header(self.infilename_bcr)
        if(bcr_header["xlength"] / bcr_header["xpixels"] -  bcr_header["ylength"] / bcr_header["ypixels"] < 0.01):
            pixel_size = bcr_header["xlength"] / bcr_header["xpixels"]
        else:
            print("Pixel size has to be the same in x and y direction")
            return(1)
            sys.exit()
        if(self.rmsd==True):
            score_type = "RMSD"
        else:
            score_type = "MAE"
        coor_list = read_pdb(self.infilename_pdb)[1]
        best_fit = coor_list # in first cykle, best fit is default rotation
        list_of_all_rots = []
        if((self.refine is False) and (self.ref_angle is None) and (self.docker_rough_output is None)):
            create_folders_object = CreateFolder(self.infilename_pdb, self.infilename_bcr, self.project_name)
        elif(self.refine is True and (self.ref_angle is not None) and (self.docker_rough_output is not None)):
            create_folders_object = CreateFolderRefine(self.infilename_pdb, self.infilename_bcr, self.project_name, self.ref_line_num)
        folder = create_folders_object.create_folder()
    
        axisangles, cor_sums, diff_matrices, aligned_pdb_matrices, angles_z, axisangles_complete = align_matrices(coor_list, bcr_header, bcr_array, self.rots_count, self.rots_count_around_z, \
                                                                                             rough_output_list=None, \
                                                                                             self.how_much_best_rots, self.glob_rots_refine, self.z_rots_refine, \
                                                                                             self.up_down_steps_count, self.corner_background, self.scale, \
                                                                                             self.rmsd, self.gauss_sigma, self.boxcar_size)
        
        if(self.autorefine is True):
            for i in range(0,self.how_much_best_rots*self.glob_rots_ref*self.z_rots_refine):
                rough_outputs_list.append(i//self.glob_rots_ref*self.z_rots_refine) # e.g. if have 5 rough outputs with 2*3 rots, then first 6 rots should be 0 etc.
            best_fits_for_ref = np.argsort(cor_sums)[::1][:len(cor_sums)]
            axisangles_complete_for_ref = []
            rough_outputs_sorted = []
            for l in range(0, len(how_much_best_rots)):
                index_for_ref = best_fits_for_ref[l]
                axisangles_complete_for_ref.append(axisangles_complete[index_for_ref]) 
                rough_outputs_sorted.append(rough_output_list[index_for_ref])
            axisangles_ref, cor_sums_ref, diff_matrices_ref, aligned_pdb_matrices_ref, angles_z_ref, axisangles_complete_ref = align_matrices(coor_list, bcr_header, bcr_array, \
                                                                                                                                              self.rots_count, self.rots_count_around_z, \
                                                                                                                                              axisangles_complete_for_ref, \
                                                                                                                                              self.how_much_best_rots, \
                                                                                                                                              self.glob_rots_ref, \
                                                                                                                                              self.z_rots_refine, \
                                                                                                                                              self.up_down_steps_count, self.corner_background, \
                                                                                                                                              self.scale, \
                                                                                                                                              self.rmsd, self.gauss_sigma, self.boxcar_size)
            for m in range(0, len(axisangles_complete_ref)):
                 axisangles_combined_with_rough.append(combine_two_axisangles(axisangles_complete[rough_outputs_sorted[m]], axisangles_complete_ref[m]))
            axisangles.extend(axisangles_ref)
            cor_sums.extend(cor_sums_ref)
            diff_matrices.extend(diff_matrices_ref)
            aligned_pdb_matrices.extend(aligned_pdb_matrices_ref)
            best_fits = np.argsort(cor_sums)[::1][:len(cor_sums)]            
            # pokracuj- axisangles append axisangles_ref (predtym ale skombinuj rough output a refinement), dalej v compare and output uprav vstupy 
        with open(str(pathlib.Path(folder, "text_output.txt")), mode="w+", encoding='utf-8') as textoutput:
            textoutput.write("Pydocker output\nPdb_file: {}\nBcr file: {}\nGlobal rotations: {}\nZ rotations: {}\nRefinement: {}\nRef. line number: {}\nRef. angle: {}\nScore type: {}\n".format(infilename_pdb, infilename_bcr, self.rots_count, self.rots_count_around_z, str(self.refine), str(self.ref_line_num), str(self.ref_angle),score_type))
            ind_best = 0
            max_vals_diff = []
            min_vals_diff = []
            max_vals_pdb = []
            min_vals_pdb = []
            for i in range(0, len(best_fits)):
                ind_best = best_fits[i]
                max_vals_diff.append(np.amax(diff_matrices[ind_best]))
                min_vals_diff.append(np.amin(diff_matrices[ind_best]))
                max_vals_pdb.append(np.amax(aligned_pdb_matrices[ind_best]))
                min_vals_pdb.append(np.amin(aligned_pdb_matrices[ind_best]))
            maxval = max(max(max_vals_diff),max(max_vals_pdb),bcr_array.max())
            minval = min(min(min_vals_diff),min(min_vals_pdb),bcr_array.min())
            ind_best = 0
            for i in range(0, len(best_fits)):
                ind_best = best_fits[i]
                axisangle_for_output = axisangles[ind_best]
                textoutput.write("score: {0:.3f} axis: {1:.5f} {2:.5f} {3:.5f} angle: {4:.5f} \n".format(cor_sums[ind_best],axisangle_for_output[0],axisangle_for_output[1],axisangle_for_output[2],axisangle_for_output[3]))
                draw_points(diff_matrices[ind_best],i,folder,cor_sums[ind_best], pixel_size, aligned_pdb_matrices[ind_best], bcr_array, self.rmsd, maxval,minval)
    
    def compare_and_output_all(self):
        
        for p in self.infilenames_pdb:
            for b in self.infilenames_bcr:
                self.compare_and_output(p,b)
        return(0)



