---
name: geospatial-science
description: Work with vector and raster geospatial data in Python, from coordinate reference systems, spatial joins and overlays in GeoPandas to satellite imagery, terrain, STAC catalogs, spatial statistics and Earth-observation machine learning. Use when data has coordinates, addresses, shapefiles, GeoPackage or GeoParquet, GeoTIFF or other rasters, when someone needs maps, distances, areas, buffers, zonal statistics, NDVI, reprojection, or spatial analysis of health, environmental or field data.
user-invocable: true
license: Apache-2.0 AND MIT
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/geopandas, skills/geomaster)"
---

# Geospatial Science

Most geospatial errors are silent: a distance computed in degrees, two layers in different
coordinate systems, a join that drops the features on a border. This skill makes the spatial
assumptions explicit before analysis. The two guides under `references/` are adapted from K-Dense
Scientific Agent Skills (MIT; see `LICENSE-UPSTREAM`).

## First questions

1. **What is the geometry?** Points (sites, patients, samples), lines (roads, rivers),
   polygons (counties, census tracts, catchments) or a raster grid (imagery, elevation,
   climate). Vector work goes through GeoPandas; raster work through Rasterio and Xarray.
2. **Which coordinate reference system (CRS) is each layer in?** Read it from the file
   (`gdf.crs`, `rasterio.open(path).crs`); never assume WGS84. A layer without a CRS needs one
   from its documentation before anything else.
3. **What will be measured?** Distances and areas need a projected CRS in metres suited to the
   region (a UTM zone, a national grid, or an equal-area projection for areas). Latitude and
   longitude are for storage and display, not measurement.
4. **Are the locations sensitive?** Home addresses, patient residences and endangered-species
   sites are identifying. Aggregate to an area, jitter with a documented radius, or keep the
   analysis inside the approved environment; the GeoPandas guide has a checklist
   (`references/geopandas/scripts/sensitive_coordinates_checklist.py`).

## Choose the path

| Task | Use | Guide |
| --- | --- | --- |
| Read, clean, reproject and join vector layers; buffers, overlays, dissolve, nearest features | GeoPandas with Shapely 2 and pyproj | `references/geopandas.md` |
| Satellite and aerial imagery, band maths (NDVI), cloud masks, terrain derivatives, resampling | Rasterio, rioxarray, Xarray | `references/geomaster.md` |
| Search and stream imagery from STAC catalogs or Earth Engine | pystac-client, odc-stac, Earth Engine API | `references/geomaster.md`, `references/geomaster/references/remote-sensing.md` |
| Spatial statistics: autocorrelation, hot spots, spatial regression, interpolation | PySAL (esda, spreg), scikit-gstat or pykrige | `references/geomaster/references/advanced-gis.md` |
| Land-cover classification and other Earth-observation ML | scikit-learn or deep learning on tiled rasters, with spatially blocked validation | `references/geomaster/references/machine-learning.md` |
| Very large vector or raster data, cloud-native formats | GeoParquet, Cloud-Optimized GeoTIFF, Zarr; Dask-GeoPandas | `references/geomaster/references/big-data.md` |

## Rules that prevent the common errors

- **Reproject explicitly**, once, to a CRS chosen for the question, and log it. Compare CRS
  objects with `==` before any overlay or join; GeoPandas only warns on a mismatch, and a
  warning in a long log is easy to miss.
- **Validate geometry** before overlays and dissolves (`make_valid`, then check for empty or
  collapsed shapes). Invalid polygons produce wrong areas without errors.
- **Name the join predicate.** `intersects`, `within` and `contains` give different answers on
  boundaries; count unmatched and multiply matched features after every `sjoin`.
- **Rasters need the same grid.** Before combining rasters, align CRS, resolution, extent and
  pixel origin; resample with a method that suits the variable (nearest for categories,
  bilinear or average for continuous values).
- **Nodata is not zero.** Read and propagate the nodata value and masks through every step.
- **Antimeridian and poles.** Global data crossing 180 degrees longitude needs splitting or a
  suitable projection; the GeoPandas guide covers the checks.
- **Spatial autocorrelation inflates confidence.** Nearby observations are not independent:
  use spatially blocked cross-validation for models and spatial error or lag models, or
  cluster-robust errors by area, for inference.

## Health and environmental data

For exposure studies (air quality, greenspace, distance to care), document the geocoding
source and match rate, the buffer sizes and why, the temporal alignment between exposure and
outcome, and the areal unit. Results that change with the choice of areal unit (the modifiable
areal unit problem) should be shown at a second unit. Statistical modelling of the linked data
goes through `statistical-modeling-bayes` or `econometrics-toolkit`; interactive maps for
sharing through `interactive-dashboards`.

## In Biorouter

- Run analyses with the Developer shell; the GeoPandas guide ships local audit tools
  (`references/geopandas/scripts/geometry_validity_report.py`,
  `references/geopandas/scripts/spatial_join_audit.py`,
  `references/geopandas/scripts/crs_reprojection_plan.py`) and GeoMaster ships raster recipes
  (`references/geomaster/scripts/raster_workflows.py`).
- Large rasters and storage layout decisions: `scientific-data-engineering`.
- Static maps follow `python-visualization` or `ggplot-visualization` (with sf in R); check
  legends, scale bars and colour maps with `figure-qa`.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/geopandas.md` | GeoSeries and GeoDataFrame, CRS rules, validity, joins and overlays, I/O (GeoParquet, PostGIS), plotting, privacy |
| `references/geomaster.md` | Remote sensing, raster recipes (NDVI, terrain, classification), STAC and Earth Engine, networks, storage |

The GeoMaster folder (`references/geomaster/references/`) adds deep notes on coordinate systems,
data sources, GIS software, spatial statistics, big data, and other languages (R, Julia,
JavaScript).
