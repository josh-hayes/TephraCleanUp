import osmnx as ox
import pandas as pd
import geopandas as gpd
import random
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats
import shutil
import glob
import os
import requests

def tephra_cleanup_volume_from_place (place, min_thickness, max_thickness, fig, csv):
    """
    This function will estimate the volume of tephra requiring removal as part of municipal clean-up efforts.
    The function requires the name of the place and the thickness of tephra in mm. The user can specifiy whether a
    graph and csv file is produced with the model results.

        Arguments:
            place (str): Name of the place for OSMnX to search the OSM database and collect the exposure data
            thickness (float): Thickness of tephra in mm to model across the urban area of interest
            fig (Bool): Defines whether a graph is produced and saved of the model results (True) or not (False)
            csv (Bool): Defines whether a csv file is generated that contains the model results (True) or not (False)
        Returns:
             Volume (Dict): Returns a Dictionary of model results at the 5th, 50th, and 95th percentile for the volume
             of tephra removal required in cubic metres
    """
    ox.config(timeout=2000)
    print("Initiating tephra clean-up model for ", place)
    substring = ","
    if place.find(substring) != -1:
        place_name_initial = place[:place.index(",")]
        place_name = place_name_initial.replace(" ", "")
        place_name_save = place_name.replace(" ", "_")
    else:
        place_name = place
        place_name_save = place_name.replace(" ", "_")
    directory = os.path.dirname(os.path.abspath(__file__))
    Geospatial_dir = directory + "/Geospatial_data/" + place_name_save
    if not os.path.exists(Geospatial_dir):
        os.makedirs(Geospatial_dir)
        print("Geospatial folder has been created")
    else:
        print("Geospatial folder already exists")

    print("Obtaining building footprints from OSM.")
    for attempt in range(10):
        try:
            try:
                buildings = ox.geometries_from_place(place, tags={"building": True}, which_result=None,
                                                     buffer_dist=None)
                break
            except (TypeError, ValueError, KeyError):
                print("OSMnX may not be able to find place. "
                      "Try using the tephra_cleanup_from_address function instead")
                exit()

        except requests.exceptions.ReadTimeout:
            print("Timeout")
    print("Reprojecting buildings to UTM")
    FP_area_UTM = ox.projection.project_gdf(buildings, to_crs=None, to_latlong=False)
    print("Calculating footprint area.")
    FP_area_UTM["area"] = FP_area_UTM['geometry'].area
    fp_area = FP_area_UTM['area'].sum()
    print("Saving building footprints to disk")
    print("Total building footprint area is: ", fp_area)
    FP_area_UTM[['area', 'geometry']].to_file(
        "Geospatial_data/" + place_name_save + "/" + place_name_save + "_buildings.gpkg", driver="GPKG",
        encoding='UTF-8')

    print("Building footprints obtained, now obtaining roads from OSM.")
    try:
        roads = ox.graph_from_place(place, network_type='drive')
    except (TypeError, ValueError, KeyError):
        print(
            "OSMnX may not be able to find location using from_place. "
            "Try using the tephra_cleanup_from_address instead")
        exit()
    print("reprojecting roads to UTM")
    road_UTM = ox.project_graph(roads)
    print("saving roads locally")
    ox.io.save_graph_geopackage(road_UTM,
                                "Geospatial_data/" + place_name_save + "/" + place_name_save + "_roads.gpkg",
                                encoding='UTF-8')
    print("Roads save locally")
    road_UTM = gpd.read_file("Geospatial_data/" + place_name_save + "/" + place_name_save + "_roads.gpkg",
                                       layer='edges')

    print("Estimating road area")
    road_UTM["area"] = road_UTM["length"] * 3
    road_area = road_UTM['area'].sum()
    print("Estimating impervious surface area based on road area")
    impervious_area = road_area
    print("Estimating building footprint area")
    fp_area = FP_area_UTM['area'].sum()
    #roads["area"] = roads["length"] * 3
    all_area = road_area + fp_area + impervious_area

    # Tephra thickness
    #Tephra_thicknesses = tephra_thickness
    # Tephra_thicknesses.fillna(0, inplace=True)
    # Study_area_thicknesses = Tephra_thicknesses[Tephra_thicknesses['City'] == Study_area]
    # Study_area_thicknesses_transpose = Study_area_thicknesses.set_index('City').T

    # ---------- Cleanup model thresholds ----------
    #Scenario = i
    print("Initiating clean-up modelling for", place)
    #max_thickness = row[Study_area]
    #Min_Model_Thickness = row[Study_area] / 2
    print("Maximum tephra thickness for", place, "is:", max_thickness, "mm. Minimum  thickness is:",
          min_thickness)
    #####
    #####
    # Clean-up thresholds
    print("Determining the appropriate clean-up threshold to use.")
    if max_thickness >= 1000:
        cleanup_area_min = all_area - (all_area * 0.1)
        cleanup_area_max = all_area + (all_area * 0.1)
    elif max_thickness >= 10:
        cleanup_area_min = (road_area - (road_area * 0.1)) + (impervious_area - (impervious_area * 0.1)) + (
                fp_area - (fp_area * 0.1))
        cleanup_area_max = (road_area + (road_area * 0.1)) + (impervious_area + (impervious_area * 0.1)) + (
                fp_area + (fp_area * 0.1))
    # elif Model_Thickness >= 10:
    #     cleanup_area_min = road_area - (road_area * 0.1)
    #     cleanup_area_max = road_area + (road_area * 0.1)
    elif max_thickness >= 0.5:
        cleanup_area_min = road_area - (road_area * 0.1)
        cleanup_area_max = road_area + (road_area * 0.1)
    elif max_thickness < 0.5:
        cleanup_area_min = 0
        cleanup_area_max = 0

    # --- Monte Carlo analysis ---
    Thickness = []
    Area = []
    Volume = []
    # Dollars=[]
    # Duration=[]

    N = 10000
    print("Calculating tephra volume requiring clean-up.")
    for i in range(N):
        DThickness = ((random.uniform((min_thickness), (max_thickness)) / 1000))
        DArea = (random.uniform((cleanup_area_min), (cleanup_area_max)))
        DVolume = (DArea * DThickness)
        # DDollars =((random.randint(Min_cost_per_m3, Max_cost_per_m3)*DVolume)/1000)
        # DDuration =((DVolume/(random.randint(Min_truck_size_m3, Max_truck_size_m3)))*
        # (random.randint(Min_disposal_time_mins,Max_disposal_time_mins)/(random.randint(Min_trucks, Max_trucks)))/
        # (random.randint(Min_hrs_day, Max_hrs_day)*60))

        Thickness = Thickness + [DThickness]
        Area = Area + [DArea]
        Volume = Volume + [DVolume]
        # Dollars=Dollars+[DDollars]
        # Duration=Duration+[DDuration]

    num_bins = 50

    df = pd.DataFrame(Volume)
    print(df.describe())

    Percentile_50 = stats.scoreatpercentile(Volume, 50)
    Percentile_10 = stats.scoreatpercentile(Volume, 10)
    Percentile_90 = stats.scoreatpercentile(Volume, 90)
    CleanUpVolume = pd.DataFrame([[place, Percentile_10, Percentile_50, Percentile_90]],
                                 columns=["Place",
                                          "10th Percentile",
                                          "50th Percentile",
                                          "90th Percentile"])
    print(CleanUpVolume)
    if csv==True:
        path_csv = "Results/" + place + "_" + ".csv"
        CleanUpVolume.to_csv(path_csv, index=False)
        path_temp = "Results/temp/" + place_name_save + "_" + ".csv"
        CleanUpVolume.to_csv(path_temp, index=False)
    else:
        print("No csv will be produced because csv=False. If you want a csv, make csv=True")

    # --- plotting the results ---
    if fig == True:
        if cleanup_area_min > 0:
            fig1 = plt.figure(figsize=(8, 8))

            ax1 = plt.subplot(3, 1, 1)
            ax1.plot(np.sort(Volume), np.linspace(0.0, 1.0, len(Volume)))
            # plt.xlabel('Volume [$m^3$]')
            plt.ylabel('Cumulative density function')
            plt.yticks([0, 0.25, 0.5, 0.75, 1])
            # ax1.axvspan(15000, 45000, alpha=0.5, color='gray')
            ax1.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))

            ax2 = plt.subplot(3, 1, 2)
            ax2.hist(np.sort(Volume), bins=50, density=True, label="Volume")
            ax2.set_ylabel('Probability Density')
            ax2.set_xlabel('Volume [$m^3$]')
            ax2.legend(loc=0, framealpha=0.5, fontsize=11)
            ax2.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))

            plt.show()

            # fig1.savefig(City_dir + "/" + place + '_volume.png', transparent=True, dpi=300,
            #              bbox_inches='tight')
            #plt.close()
        else:
            print("No ash expected to require removal. No graph will be made")
    else:
        print ("No figure will be produced because fig=False. If you want a figure make fig=True")

    return()

def tephra_cleanup_volume_from_point (point, buffer, place, min_thickness, max_thickness, fig, csv):
    """
    This function will estimate the volume of tephra requiring removal as part of municipal clean-up efforts.
    The function requires the name of the place and the thickness of tephra in mm. The user can specifiy whether a
    graph and csv file is produced with the model results.

        Arguments:
            place (str): Name of the place for OSMnX to search the OSM database and collect the exposure data
            thickness (float): Thickness of tephra in mm to model across the urban area of interest
            fig (Bool): Defines whether a graph is produced and saved of the model results (True) or not (False)
            csv (Bool): Defines whether a csv file is generated that contains the model results (True) or not (False)
        Returns:
             Volume (Dict): Returns a Dictionary of model results at the 5th, 50th, and 95th percentile for the volume
             of tephra removal required in cubic metres
    """
    ox.config(timeout=2000)
    print("Initiating tephra clean-up model for ", place)
    substring = ","
    if place.find(substring) != -1:
        place_name_initial = place[:place.index(",")]
        place_name = place_name_initial.replace(" ", "")
        place_name_save = place_name.replace(" ", "_")
    else:
        place_name = place
        place_name_save = place_name.replace(" ", "_")
    directory = os.path.dirname(os.path.abspath(__file__))
    Geospatial_dir = directory + "/Geospatial_data/" + place_name_save
    if not os.path.exists(Geospatial_dir):
        os.makedirs(Geospatial_dir)
        print("Geospatial folder has been created")
    else:
        print("Geospatial folder already exists")

    print("Obtaining building footprints from OSM.")
    for attempt in range(10):
        try:
            try:
                buildings = ox.geometries_from_point(point, tags={"building": True},
                                                     dist=buffer)
                break
            except (TypeError, ValueError, KeyError):
                print("OSMnX may not be able to find place. "
                      "Try using a different function instead")
                exit()

        except requests.exceptions.ReadTimeout:
            print("Timeout")
    print("Reprojecting buildings to UTM")
    FP_area_UTM = ox.projection.project_gdf(buildings, to_crs=None, to_latlong=False)
    print("Calculating footprint area.")
    FP_area_UTM["area"] = FP_area_UTM['geometry'].area
    fp_area = FP_area_UTM['area'].sum()
    print("Saving building footprints to disk")
    # FP_area_UTM[['area', 'geometry']].to_file(
    #     "Geospatial_data/" + Study_area_name + "/" + Study_area_name + "_buildings.gpkg", driver="GPKG",
    #     encoding='UTF-8')

    print("Building footprints obtained, now obtaining roads from OSM.")
    try:
        roads = ox.graph_from_point(point, network_type='drive', dist=buffer)
    except (TypeError, ValueError, KeyError):
        print(
            "OSMnX may not be able to find location using from_place. "
            "Try using the tephra_cleanup_from_address instead")
        exit()
    print("reprojecting roads to UTM")
    road_UTM = ox.project_graph(roads)
    print("saving roads locally")
    ox.io.save_graph_geopackage(road_UTM,
                                "Geospatial_data/" + place_name + "/" + place_name + "_roads.gpkg",
                                encoding='UTF-8')
    print("Roads save locally")
    road_UTM = gpd.read_file("Geospatial_data/" + place_name + "/" + place_name + "_roads.gpkg",
                                       layer='edges')

    print("Estimating road area")
    road_UTM["area"] = road_UTM["length"] * 3
    road_area = road_UTM['area'].sum()
    print("Estimating impervious surface area based on road area")
    impervious_area = road_area
    print("Estimating building footprint area")

    all_area = road_area + fp_area + impervious_area

    # ---------- Cleanup model thresholds ----------

    print("Initiating clean-up modelling for", place)

    print("Maximum tephra thickness for", place, "is:", max_thickness, "mm. Minimum  thickness is:",
          min_thickness)
    #####
    #####
    # Clean-up thresholds
    print("Determining the appropriate clean-up threshold to use.")
    if max_thickness >= 1000:
        cleanup_area_min = all_area - (all_area * 0.1)
        cleanup_area_max = all_area + (all_area * 0.1)
    elif max_thickness >= 10:
        cleanup_area_min = (road_area - (road_area * 0.1)) + (impervious_area - (impervious_area * 0.1)) + (
                fp_area - (fp_area * 0.1))
        cleanup_area_max = (road_area + (road_area * 0.1)) + (impervious_area + (impervious_area * 0.1)) + (
                fp_area + (fp_area * 0.1))
    elif max_thickness >= 0.5:
        cleanup_area_min = road_area - (road_area * 0.1)
        cleanup_area_max = road_area + (road_area * 0.1)
    elif max_thickness < 0.5:
        cleanup_area_min = 0
        cleanup_area_max = 0

    # --- Monte Carlo analysis ---
    Thickness = []
    Area = []
    Volume = []
    # Dollars=[]
    # Duration=[]

    N = 10000
    print("Calculating tephra volume requiring clean-up.")
    for i in range(N):
        DThickness = ((random.uniform((min_thickness), (max_thickness)) / 1000))
        DArea = (random.uniform((cleanup_area_min), (cleanup_area_max)))
        DVolume = (DArea * DThickness)
        # DDollars =((random.randint(Min_cost_per_m3, Max_cost_per_m3)*DVolume)/1000)
        # DDuration =((DVolume/(random.randint(Min_truck_size_m3, Max_truck_size_m3)))*
        # (random.randint(Min_disposal_time_mins,Max_disposal_time_mins)/(random.randint(Min_trucks, Max_trucks)))/
        # (random.randint(Min_hrs_day, Max_hrs_day)*60))

        Thickness = Thickness + [DThickness]
        Area = Area + [DArea]
        Volume = Volume + [DVolume]
        # Dollars=Dollars+[DDollars]
        # Duration=Duration+[DDuration]

    num_bins = 50

    df = pd.DataFrame(Volume)
    print(df.describe())

    Percentile_50 = stats.scoreatpercentile(Volume, 50)
    Percentile_10 = stats.scoreatpercentile(Volume, 10)
    Percentile_90 = stats.scoreatpercentile(Volume, 90)
    CleanUpVolume = pd.DataFrame([[place, Percentile_10, Percentile_50, Percentile_90]],
                                 columns=["Place",
                                          "10th Percentile",
                                          "50th Percentile",
                                          "90th Percentile"])
    print(CleanUpVolume)
    if csv==True:
        path_csv = "Results/" + place + "_" + ".csv"
        CleanUpVolume.to_csv(path_csv, index=False)
        path_temp = "Results/temp/" + place_name_save + "_" + ".csv"
        CleanUpVolume.to_csv(path_temp, index=False)
    else:
        print("No csv will be produced because csv=False. If you want a csv, make csv=True")

    # --- plotting the results ---
    if fig == True:
        if cleanup_area_min > 0:
            fig1 = plt.figure(figsize=(8, 8))

            ax1 = plt.subplot(3, 1, 1)
            ax1.plot(np.sort(Volume), np.linspace(0.0, 1.0, len(Volume)))
            # plt.xlabel('Volume [$m^3$]')
            plt.ylabel('Cumulative density function')
            plt.yticks([0, 0.25, 0.5, 0.75, 1])
            # ax1.axvspan(15000, 45000, alpha=0.5, color='gray')
            ax1.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))

            ax2 = plt.subplot(3, 1, 2)
            ax2.hist(np.sort(Volume), bins=50, density=True, label="Volume")
            ax2.set_ylabel('Probability Density')
            ax2.set_xlabel('Volume [$m^3$]')
            ax2.legend(loc=0, framealpha=0.5, fontsize=11)
            ax2.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))

            plt.show()

            # fig1.savefig(City_dir + "/" + place + '_volume.png', transparent=True, dpi=300,
            #              bbox_inches='tight')
            #plt.close()
        else:
            print("No ash expected to require removal. No graph will be made")
    else:
        print ("No figure will be produced because fig=False. If you want a figure make fig=True")

    return()

def tephra_cleanup_volume_from_isopach (name, isopach, fig, csv):
    """

    :param area:
    :param isopach:
    :param fig:
    :param csv:
    :return:
    """
    ox.config(timeout=2000)
    directory = os.path.dirname(os.path.abspath(__file__))
    Geospatial_dir = directory + "/Geospatial_data/" + name
    if not os.path.exists(Geospatial_dir):
        os.makedirs(Geospatial_dir)
        print("Geospatial folder has been created")
    else:
        print("Geospatial folder already exists")

    print("Obtaining building footprints from OSM.")
    isopach = isopach.to_crs("EPSG:4326")
    isopach_geom = isopach
    isopach_geom['dissolve'] = 1
    isopach_geom = isopach_geom.dissolve(by='dissolve')
    isopach_geom = isopach_geom["geometry"].iloc[0]
    for attempt in range(10):
        try:
            try:
                buildings = ox.geometries_from_polygon(isopach_geom, tags={"building": True})
                break
            except (TypeError, ValueError, KeyError):
                print("Error")
                exit()

        except requests.exceptions.ReadTimeout:
            print("Timeout")
    print("Reprojecting buildings to UTM")
    FP_area_UTM = ox.projection.project_gdf(buildings, to_crs=None, to_latlong=False)
    print("Calculating footprint area.")
    FP_area_UTM["area"] = FP_area_UTM['geometry'].area
    fp_area = FP_area_UTM['area'].sum()
    print("Saving building footprints to disk")
    FP_area_UTM[['area', 'geometry']].to_file(
        "Geospatial_data/" + name + "/" + name + "_buildings.gpkg", driver="GPKG",
        encoding='UTF-8')

    print("Building footprints obtained, now obtaining roads from OSM.")
    try:
        roads = ox.graph_from_polygon(isopach_geom, network_type='drive')
    except (TypeError, ValueError, KeyError):
        print(
            "Error")
        exit()
    print("reprojecting roads to UTM")
    road_UTM = ox.project_graph(roads)
    print("saving roads locally")
    ox.io.save_graph_geopackage(road_UTM,
                                "Geospatial_data/" + name + "/" + name + "_roads.gpkg",
                                encoding='UTF-8')
    print("Roads saved locally")
    road_UTM = gpd.read_file("Geospatial_data/" + name + "/" + name + "_roads.gpkg",
                                   layer='edges')

    print("Estimating road area")
    road_UTM["area"] = road_UTM["length"] * 3
    road_area = road_UTM['area'].sum()
    print("Estimating impervious surface area based on road area")
    impervious_area = road_area
    print("Estimating building footprint area")
    fp_area = FP_area_UTM['area'].sum()
    all_area = road_area + fp_area + impervious_area


    # ---------- Cleanup model thresholds ----------
    print("Initiating clean-up modelling for", name)


    #####
    #####
    crs = road_UTM.crs
    isopach = isopach.to_crs(crs)
    FP_area_UTM = FP_area_UTM.to_crs(crs)
    Thickness_buildings = gpd.sjoin(FP_area_UTM, isopach, how="inner", op='intersects')
    Thickness_buildings['volume_min'] = Thickness_buildings['area']*(Thickness_buildings['min_thick']/1000)
    Thickness_buildings['volume_max'] = Thickness_buildings['area']*(Thickness_buildings['max_thick']/1000)

    Thickness_roads = gpd.sjoin(road_UTM, isopach, how="inner", op='intersects')
    Thickness_roads['volume_min'] = Thickness_roads['area']*(Thickness_roads['min_thick']/1000)
    Thickness_roads['volume_max'] = Thickness_roads['area']*(Thickness_roads['max_thick']/1000)


    # Clean-up thresholds
    print("Determining the appropriate clean-up threshold to use.")
    # high thickness areas
    zone_1_buildings_min = Thickness_buildings.loc[Thickness_buildings['min_thick'] >= 1000]
    zone_1_buildings_volume_min = zone_1_buildings_min['volume_min'].sum()
    zone_1_roads_min = Thickness_roads.loc[Thickness_roads['min_thick']>=1000]
    zone_1_roads_volume_min = zone_1_roads_min['volume_min'].sum()

    zone_1_buildings_max = Thickness_buildings.loc[Thickness_buildings['max_thick'] >= 1000]
    zone_1_buildings_volume_max = zone_1_buildings_max['volume_max'].sum()
    zone_1_roads_max = Thickness_roads.loc[Thickness_roads['max_thick']>=1000]
    zone_1_roads_volume_max = zone_1_roads_max['volume_max'].sum()

    zone_1_volume_min = (zone_1_buildings_volume_min + (zone_1_roads_volume_min*2)) - ((zone_1_buildings_volume_min + (zone_1_roads_volume_min*2))*0.1)
    zone_1_volume_max = (zone_1_buildings_volume_max + (zone_1_roads_volume_max*2)) + ((zone_1_buildings_volume_max + (zone_1_roads_volume_max*2))*0.1)

    #medium thickness areas
    zone_2_buildings_min = Thickness_buildings.loc[Thickness_buildings['min_thick'] >= 10]
    zone_2_buildings_volume_min = zone_2_buildings_min['volume_min'].sum()
    zone_2_roads_min = Thickness_roads.loc[Thickness_roads['min_thick']>=10]
    zone_2_roads_volume_min = zone_2_roads_min['volume_min'].sum()

    zone_2_buildings_max = Thickness_buildings.loc[Thickness_buildings['max_thick'] >= 10]
    zone_2_buildings_volume_max = zone_2_buildings_max['volume_max'].sum()
    zone_2_roads_max = Thickness_roads.loc[Thickness_roads['max_thick']>=10]
    zone_2_roads_volume_max = zone_2_roads_max['volume_max'].sum()


    zone_2_volume_min = (zone_2_buildings_volume_min + (zone_2_roads_volume_min*2)) - ((zone_2_buildings_volume_min + (zone_2_roads_volume_min*2))*0.1)
    zone_2_volume_max = (zone_2_buildings_volume_max + (zone_2_roads_volume_max*2)) + ((zone_2_buildings_volume_max + (zone_2_roads_volume_max*2))*0.1)

    #Low thickness areas
    zone_3_roads_min = Thickness_roads.loc[Thickness_roads['min_thick']>=0.5]
    zone_3_roads_volume_min = zone_3_roads_min['volume_min'].sum()
    zone_3_volume_min = (zone_3_roads_volume_min + (zone_3_roads_volume_min *0.1))

    zone_3_roads_max = Thickness_roads.loc[Thickness_roads['max_thick'] >= 0.5]
    zone_3_roads_volume_max = zone_3_roads_max['volume_max'].sum()
    zone_3_volume_max = (zone_3_roads_volume_max + (zone_3_roads_volume_max * 0.1))


    zone_3_volume_max = (zone_3_roads_volume_max + (zone_3_roads_volume_max *0.1))

    cleanup_volume_min = zone_1_volume_min + zone_2_volume_min + zone_3_volume_min
    cleanup_volume_max = zone_1_volume_max + zone_2_volume_max + zone_3_volume_max

    # --- Monte Carlo analysis ---
    Thickness = []
    Area = []
    Volume = []
    # Dollars=[]
    # Duration=[]

    N = 10000
    print("Calculating tephra volume requiring clean-up.")
    for i in range(N):
        DVolume = ((random.uniform((cleanup_volume_min), (cleanup_volume_max))))
        # DDollars =((random.randint(Min_cost_per_m3, Max_cost_per_m3)*DVolume)/1000)
        # DDuration =((DVolume/(random.randint(Min_truck_size_m3, Max_truck_size_m3)))*
        # (random.randint(Min_disposal_time_mins,Max_disposal_time_mins)/(random.randint(Min_trucks, Max_trucks)))/
        # (random.randint(Min_hrs_day, Max_hrs_day)*60))

        Volume = Volume + [DVolume]
        # Dollars=Dollars+[DDollars]
        # Duration=Duration+[DDuration]

    num_bins = 50

    df = pd.DataFrame(Volume)
    print(df.describe())

    Percentile_50 = stats.scoreatpercentile(Volume, 50)
    Percentile_10 = stats.scoreatpercentile(Volume, 10)
    Percentile_90 = stats.scoreatpercentile(Volume, 90)
    CleanUpVolume = pd.DataFrame([[name, Percentile_10, Percentile_50, Percentile_90]],
                                 columns=["Place",
                                          "10th Percentile",
                                          "50th Percentile",
                                          "90th Percentile"])
    print(CleanUpVolume)
    if csv==True:
        path_csv = "Results/" + name + "_" + ".csv"
        CleanUpVolume.to_csv(path_csv, index=False)
        path_temp = "Results/temp/" + name + "_" + ".csv"
        CleanUpVolume.to_csv(path_temp, index=False)
    else:
        print("No csv will be produced because csv=False. If you want a csv, make csv=True")

    # --- plotting the results ---
    if fig == True:
        if Percentile_10 > 0:
            fig1 = plt.figure(figsize=(8, 8))

            ax1 = plt.subplot(3, 1, 1)
            ax1.plot(np.sort(Volume), np.linspace(0.0, 1.0, len(Volume)))
            # plt.xlabel('Volume [$m^3$]')
            plt.ylabel('Cumulative density function')
            plt.yticks([0, 0.25, 0.5, 0.75, 1])
            # ax1.axvspan(15000, 45000, alpha=0.5, color='gray')
            ax1.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))

            ax2 = plt.subplot(3, 1, 2)
            ax2.hist(np.sort(Volume), bins=50, density=True, label="Volume")
            ax2.set_ylabel('Probability Density')
            ax2.set_xlabel('Volume [$m^3$]')
            ax2.legend(loc=0, framealpha=0.5, fontsize=11)
            ax2.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))

            plt.show()

            # fig1.savefig(City_dir + "/" + place + '_volume.png', transparent=True, dpi=300,
            #              bbox_inches='tight')
            #plt.close()
        else:
            print("No ash expected to require removal. No graph will be made")
    else:
        print ("No figure will be produced because fig=False. If you want a figure make fig=True")

    return()

def tephra_cleanup_volume_from_raser (area, raster, fig, csv):
    """

    :param area:
    :param raster:
    :param fig:
    :param csv:
    :return:
    """
    return()

