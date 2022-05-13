import pandas as pd
import geopandas as gpd
import json
import matplotlib as mpl
import pylab as plt

from bokeh.io import output_file, show, output_notebook, export_png
from bokeh.models import ColumnDataSource, GeoJSONDataSource, LinearColorMapper, ColorBar, HoverTool
from bokeh.plotting import figure
from bokeh.palettes import brewer

import panel as pn
import panel.widgets as pnw

import pickle
import param

# Loading pickles:
# Optional: We can either obtain the datasets in another python file and load them here via pickle !OR! put everything in this python file and not use pickles.
with open('df_nat_gas_ru.pickle', 'rb') as handle:
    df_gas = pickle.load(handle)
with open('df_oil_petrol_ru.pickle', 'rb') as handle:
    df_oil = pickle.load(handle)
with open('df_solid_fuel_ru.pickle', 'rb') as handle:
    df_solid = pickle.load(handle)
with open('gdf.pickle', 'rb') as handle:
    gdf = pickle.load(handle)
with open('df_sitc.pickle', 'rb') as handle:
    df_sitc = pickle.load(handle)
gdf.crs = {"init":"epsg:4326"}

def get_dataset(name,key=None,year=None):
    global datasetname
    if (name == "Natural Gas"):
        df = df_gas[df_gas['Year'] == year]
        datasetname='Natural Gas'
    elif (name == "Oil Petrol"):
        df = df_oil[df_oil['Year'] == year]
        datasetname='Oil Petrol'
    elif (name == "Solid Fuel"):
        df = df_solid[df_solid['Year'] == year]
        datasetname='Solid Fuel'
    merged = gdf.merge(df, on='Country', how='left')
    key = 'Import' 
    return merged, key

datasetname='Natural Gas'
data,key = get_dataset(datasetname, year=2000) # KEY = COLUMN NAME, DATA = DATA
fig, ax = plt.subplots(1, figsize=(14, 8))
data.plot(column=key, cmap='Greens', linewidth=0.8, ax=ax, edgecolor='black')
ax.axis('off')
ax.set_title('%s 2000' %datasetname, fontsize=18)

def get_geodatasource(gdf):    
    """Get getjsondatasource from geopandas object"""
    json_data = json.dumps(json.loads(gdf.to_json()))
    return GeoJSONDataSource(geojson = json_data)

# Define custom tick labels for color bar.
tick_labels = {'0': '0%', '20': '20%', '40': '40%', '60': '60%', '80': '80%', '100': '100%',}

def bokeh_plot_map(gdf, column=None, title=''):
    """Plot bokeh map from GeoJSONDataSource """
    global datasetname
    geosource = get_geodatasource(gdf)
    if datasetname == "Natural Gas":
        palette = brewer['Greens'][8]
    elif datasetname == "Oil Petrol":
        palette = brewer['Blues'][8]
    elif datasetname == "Solid Fuel":
        palette = brewer['Oranges'][8]
    palette = palette[::-1]
    vals = gdf[column]

    hover = HoverTool(tooltips=[('Country: ', '@Country'),
                                ('Russian {} Import'.format(datasetname), '@Import')])
    #Instantiate LinearColorMapper that linearly maps numbers in a range, into a sequence of colors.
    color_mapper = LinearColorMapper(palette=palette, low=0, high=100)
    color_bar = ColorBar(color_mapper=color_mapper, label_standoff=8, height=660, width=20,
                         location=(0, 0), orientation='vertical', border_line_color=None, major_label_overrides=tick_labels)

    tools = 'wheel_zoom,pan,reset,hover'
    p = figure(title = title, plot_height=400 , plot_width=850, toolbar_location='right', tools=tools)
    p.xaxis.visible = False
    p.yaxis.visible = False
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    #Add patch renderer to figure
    p.patches('xs','ys', source=geosource, fill_alpha=1, line_width=0.5, line_color='black',  
              fill_color={'field' :column , 'transform': color_mapper})
    #Specify figure layout.
    p.add_layout(color_bar, 'right')
    p.add_tools(hover)
    return p

# ref.: https://stackoverflow.com/questions/57301630/trigger-event-on-mouseup-instead-of-continuosly-with-panel-slider-widget
class IntThrottledSlider(pnw.IntSlider):
    value_throttled = param.Integer(default=0)

def map_dash():
    """Map dashboard"""
    from bokeh.models.widgets import DataTable
    map_pane = pn.pane.Bokeh(width=900, height=700)
    data_select = pnw.Select(name='dataset',options=['Natural Gas', 'Oil Petrol', 'Solid Fuel'])
    year_slider = pnw.IntSlider(name='Year',start=2000,end=2020,value=2000,callback_policy='mouseup')
    def update_map(event):
        gdf,key = get_dataset(name=data_select.value,year=year_slider.value)        
        map_pane.object = bokeh_plot_map(gdf, key)        
        return
    year_slider.param.watch(update_map,'value_throttled')
    year_slider.param.trigger('value_throttled')
    data_select.param.watch(update_map,'value')
    app = pn.Column(pn.Row(data_select,year_slider),map_pane)
    app.servable()
    return app

app = map_dash()
