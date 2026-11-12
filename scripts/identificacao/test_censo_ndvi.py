"""Verifica o censo com uma grade analítica: centros, sobreposição e NoData."""
from contextlib import redirect_stdout
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np
from osgeo import gdal
from shapely.geometry import box

from calcular_censo_ndvi import aligned_sources, rasterize_mask, summarize, check_counts, BINS


class CensusTest(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.dry = np.linspace(-.8, .8, 80, dtype=np.float32).reshape(8, 10)
        self.rain = np.clip(self.dry + np.float32(.15), -1, 1)
        self.dry[0, 0] = np.nan
        self.rain[0, 1] = 2
        self.dry[0, 2] = -9999
        self.dry[-1, -2:] = [-1, 1]
        self.rain[-1, -2:] = [-1, 1]
        self.paired = np.isfinite(self.dry) & (self.dry >= -1) & (self.dry <= 1) & (self.rain >= -1) & (self.rain <= 1)
        mean = np.full(self.dry.shape, -9999, dtype=np.float32)
        mean[self.paired] = (self.dry[self.paired] + self.rain[self.paired]) / np.float32(2)
        wet = np.full((10, 14), -9999, dtype=np.float32)
        wet[1:9, 2:12] = self.rain
        self.paths = {}
        for name, array, transform in [('seca', self.dry, (0, 3, 0, 24, 0, -3)),
                ('chuva', wet, (-6, 3, 0, 27, 0, -3)), ('media', mean, (0, 3, 0, 24, 0, -3))]:
            path = self.folder / (name + '.tif')
            ds = gdal.GetDriverByName('GTiff').Create(str(path), array.shape[1], array.shape[0], 1, gdal.GDT_Float32)
            ds.SetGeoTransform(transform)
            ds.SetProjection('EPSG:31983')
            ds.GetRasterBand(1).SetNoDataValue(-9999)
            ds.GetRasterBand(1).WriteArray(array)
            ds = None
            self.paths[name] = path
        self.sources, self.offsets = aligned_sources(self.paths)
        self.masks = {name: rasterize_mask(self.folder / (name + '.tif'), shape, self.sources['seca'])
                      for name, shape in [('a', box(1.6, 0, 15, 24)), ('b', box(12, 0, 30, 24))]}

    def tearDown(self):
        self.sources.clear()
        self.masks.clear()
        self.temp.cleanup()

    def test_every_center_and_independent_masks(self):
        with redirect_stdout(io.StringIO()):
            groups, _, total = summarize(self.sources, self.offsets, self.masks, rows=3)
        self.assertEqual(self.offsets['chuva'], (2, 1))
        self.assertEqual(total, int(self.paired.sum()))
        x = np.arange(10) * 3 + 1.5
        for name, columns in [('a', (x > 1.6) & (x < 15)), ('b', x > 12)]:
            selected = np.broadcast_to(columns, self.dry.shape) & self.paired
            group = groups[name]
            self.assertEqual(group['n_referencia'], int(columns.sum()) * 8)
            self.assertEqual(group['n_pares_validos'], int(selected.sum()))
            for season, array in [('seca', self.dry), ('chuva', self.rain)]:
                expected = array[selected].astype(np.float64)
                self.assertAlmostEqual(group['estatisticas'][season]['media'], expected.mean(), places=13)
                self.assertAlmostEqual(group['estatisticas'][season]['desvio_padrao'], expected.std(ddof=0), places=13)
                self.assertEqual(group['histogramas'][season], np.histogram(expected, bins=BINS)[0].tolist())
            joint = np.histogram2d(self.dry[selected], self.rain[selected], bins=(BINS, BINS))[0]
            np.testing.assert_array_equal(group['densidade_conjunta'], joint)
        check_counts(groups)

    def test_different_stripes_same_population(self):
        with redirect_stdout(io.StringIO()):
            first = summarize(self.sources, self.offsets, self.masks, rows=2)[0]
            second = summarize(self.sources, self.offsets, self.masks, rows=5)[0]
        for name in first:
            self.assertEqual(first[name]['histogramas'], second[name]['histogramas'])
            self.assertEqual(first[name]['densidade_conjunta'], second[name]['densidade_conjunta'])
            for season in ('seca', 'chuva', 'media'):
                for statistic in ('media', 'desvio_padrao'):
                    self.assertAlmostEqual(first[name]['estatisticas'][season][statistic],
                                           second[name]['estatisticas'][season][statistic], places=13)

    def test_reject_misaligned_grid(self):
        self.sources.clear()
        ds = gdal.Open(str(self.paths['chuva']), gdal.GA_Update)
        ds.SetGeoTransform((-4.5, 3, 0, 27, 0, -3))
        ds = None
        with self.assertRaisesRegex(ValueError, 'deslocamento inteiro'):
            aligned_sources(self.paths)

    def test_reject_mean_with_only_one_valid_date(self):
        self.sources.pop('media')
        ds = gdal.Open(str(self.paths['media']), gdal.GA_Update)
        values = ds.ReadAsArray()
        values[0, 0] = .2  # Seca inválida: o raster médio estrito deve ser NoData.
        ds.GetRasterBand(1).WriteArray(values)
        ds = None
        self.sources['media'] = gdal.Open(str(self.paths['media']), gdal.GA_ReadOnly)
        with self.assertRaisesRegex(ValueError, 'Validade do raster médio estrito'):
            summarize(self.sources, self.offsets, self.masks)


if __name__ == '__main__':
    unittest.main()
