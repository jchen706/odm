import os

from opendm import context
from opendm import types
from opendm import io
from opendm import system
from opendm import log

from dataset import ODMLoadDatasetStage
from run_opensfm import ODMOpenSfMStage
from mve import ODMMveStage
from odm_slam import ODMSlamStage
from odm_meshing import ODMeshingStage
from mvstex import ODMMvsTexStage
from odm_georeferencing import ODMGeoreferencingStage
from odm_orthophoto import ODMOrthoPhotoStage
from odm_dem import ODMDEMStage
from odm_filterpoints import ODMFilterPoints
from splitmerge import ODMSplitStage, ODMMergeStage
from odm_report import ODMReport
import time


class ODMApp:
    def __init__(self, args):
        """
        Initializes the application and defines the ODM application pipeline stages
        """
        if args.debug:
            log.logger.show_debug = True
        
        # start = time.perf_counter()
        dataset = ODMLoadDatasetStage('dataset', args, progress=5.0,
                                          verbose=args.verbose)
        # dataset_time = time.perf_counter() - start
        split = ODMSplitStage('split', args, progress=75.0)
        # split_time = time.perf_counter() - dataset_time
        merge = ODMMergeStage('merge', args, progress=100.0)
        # merge_time = time.perf_counter() - split_time
        opensfm = ODMOpenSfMStage('opensfm', args, progress=25.0)

        # opensfm_time = time.perf_counter() - merge_time
        slam = ODMSlamStage('slam', args)
        # slam_time = time.perf_counter() - opensfm_time
        mve = ODMMveStage('mve', args, progress=50.0)
        # mve_time = time.perf_counter() - slam_time
        filterpoints = ODMFilterPoints('odm_filterpoints', args, progress=52.0)
        # fileterpoint_time = time.perf_counter() - mve_time
        meshing = ODMeshingStage('odm_meshing', args, progress=60.0,
                                    max_vertex=args.mesh_size,
                                    oct_tree=args.mesh_octree_depth,
                                    samples=args.mesh_samples,
                                    point_weight=args.mesh_point_weight,
                                    max_concurrency=args.max_concurrency,
                                    verbose=args.verbose)
        # meshing_time = time.perf_counter() - fileterpoint_time
        
        texturing = ODMMvsTexStage('mvs_texturing', args, progress=70.0,
                                    data_term=args.texturing_data_term,
                                    outlier_rem_type=args.texturing_outlier_removal_type,
                                    skip_vis_test=args.texturing_skip_visibility_test,
                                    skip_glob_seam_leveling=args.texturing_skip_global_seam_leveling,
                                    skip_loc_seam_leveling=args.texturing_skip_local_seam_leveling,
                                    skip_hole_fill=args.texturing_skip_hole_filling,
                                    keep_unseen_faces=args.texturing_keep_unseen_faces,
                                    tone_mapping=args.texturing_tone_mapping)

        # texturing_time = time.perf_counter() - meshing_time
        georeferencing = ODMGeoreferencingStage('odm_georeferencing', args, progress=80.0,
                                                    gcp_file=args.gcp,
                                                    verbose=args.verbose)
        # georeferencing_time = time.perf_counter() - texturing_time
        dem = ODMDEMStage('odm_dem', args, progress=90.0,
                            max_concurrency=args.max_concurrency,
                            verbose=args.verbose)
        # dem_time = time.perf_counter - georeferencing_time
        orthophoto = ODMOrthoPhotoStage('odm_orthophoto', args, progress=98.0)
        

        report = ODMReport('odm_report', args, progress=100.0)

        # Normal pipeline
        self.first_stage = dataset

        dataset.connect(split) \
                .connect(merge) \
                .connect(opensfm)

        if args.use_opensfm_dense or args.fast_orthophoto:
            opensfm.connect(filterpoints)
        else:
            opensfm.connect(mve) \
                    .connect(filterpoints)
        
        filterpoints \
            .connect(meshing) \
            .connect(texturing) \
            .connect(georeferencing) \
            .connect(dem) \
            .connect(orthophoto) \
            .connect(report)
                
        # # SLAM pipeline
        # # TODO: this is broken and needs work
        # log.ODM_WARNING("SLAM module is currently broken. We could use some help fixing this. If you know Python, get in touch at https://community.opendronemap.org.")
        # self.first_stage = slam

        # slam.connect(mve) \
        #     .connect(meshing) \
        #     .connect(texturing)

    def execute(self):
        self.first_stage.run()