""" Datasets for COCO challenge tasks, http://cocodataset.org/#home.
    Yet contains only the dataset for Semantic Segmentation. """

import os
import tempfile
from glob import glob
from zipfile import ZipFile
from os.path import dirname, basename

import tqdm
import requests
from PIL import Image

from . import ImagesOpenset
from .. import FilesIndex, any_action_failed, parallel, ImagesBatch, inbatch_parallel


class BaseCOCO(ImagesOpenset):
    """ Base class for COCO datasets. """

    TRAIN_IMAGES_URL = 'http://images.cocodataset.org/zips/train2017.zip'
    TEST_IMAGES_URL = 'http://images.cocodataset.org/zips/val2017.zip'
    IMAGES_URLS = [TRAIN_IMAGES_URL, TEST_IMAGES_URL]


    def __init__(self, *args, preloaded=None, **kwargs):
        super().__init__(*args, preloaded=preloaded, **kwargs)


    @parallel(init='_get_from_urls', post='_post_fn', target='t')
    def download(self, url, folder, train_val, path=None):
        """ Download the archives and extracts it's content. Downloading is performed in parallel manner.
        Set of URL's to download from is defined in the `_get_from_urls` method.
        The aggregation of the content from all archives is performed in `_post_fn` method.
        """
        logger.info('Downloading %s', url)
        if path is None:
            path = tempfile.gettempdir()
        filename = basename(url)
        localname = os.path.join(path, filename)
        if not os.path.isfile(localname):
            r = requests.get(url, stream=True)
            file_size = int(r.headers['Content-Length'])
            chunk = 1
            chunk_size = 1024 * 1000 #MBs
            num_bars = int(file_size / chunk_size)
            with open(localname, 'wb') as f:
                for chunk in tqdm.tqdm(r.iter_content(chunk_size=chunk_size), total=num_bars,
                                       unit='MB', desc=filename, leave=True):
                    f.write(chunk)
        return self._extract_if_not_exist(localname, folder, train_val)


class COCOSegmentation(BaseCOCO):
    """ The dataset for COCO """
    MASKS_URL = 'http://calvin.inf.ed.ac.uk/wp-content/uploads/data/cocostuffdataset/stuffthingmaps_trainval2017.zip'


    def __init__(self, *args, drop_grayscale=True, **kwargs):
        self.drop_grayscale = drop_grayscale
        super().__init__(*args, **kwargs)


    @property
    def _get_from_urls(self):
        """ List of URL to download from, folder where to extract, and indicator whether its train or val part. """
        iterator = zip([self.TRAIN_IMAGES_URL, self.TEST_IMAGES_URL, self.MASKS_URL, self.MASKS_URL],
                       ['COCOImages', 'COCOImages', 'COCOMasks', 'COCOMasks'],
                       ['train2017', 'val2017', 'train2017', 'val2017'])
        return [[url, folder, train_val] for url, folder, train_val in iterator]

    def _extract_archive(self, localname, extract_to):
        with ZipFile(localname, 'r') as archive:
            archive.extractall(extract_to)

    def _extract_if_not_exist(self, localname, folder, train_val):
        """ Extracts the arcive to the specific folder. Returns the path to this filder"""
        extract_to = os.path.join(dirname(localname), folder)
        path = os.path.join(extract_to, train_val)
        if os.path.isdir(path):
            pass
        else:
            self._extract_archive(localname, extract_to)
        return path

    def _rgb_images_paths(self, path):
        return  [filename for filename in glob(path + '/*') if Image.open(filename).mode == 'RGB']

    def _post_fn(self, all_res, *args, **kwargs):
        _ = args, kwargs
        if any_action_failed(all_res):
            raise IOError('Could not download files:', all_res)
 
        if self.drop_grayscale:
            self._train_index = FilesIndex(path=self._rgb_images_paths(all_res[0]), no_ext=True) 
            self._test_index = FilesIndex(path=self._rgb_images_paths(all_res[1]), no_ext=True)  
        else:
            self._train_index = FilesIndex(path=all_res[0] + '/*', no_ext=True)
            self._test_index = FilesIndex(path=all_res[1] + '/*', no_ext=True)

        # store the paths to the folders with masks as attributes
        self.path_train_masks, self.path_test_masks = all_res[2], all_res[3]
        return None, FilesIndex.concat(self._train_index, self._test_index)
