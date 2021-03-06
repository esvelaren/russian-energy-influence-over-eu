import pandas as pd
import geopandas as gpd
import json
import numpy as np
from bokeh.models import ColumnDataSource, GeoJSONDataSource, LinearColorMapper, ColorBar, HoverTool, Range1d, Selection
from bokeh.models.widgets.tables import NumberFormatter
from bokeh.plotting import figure
from bokeh.palettes import brewer
import panel as pn
import panel.widgets as pnw
import plotly.express as px
import pickle
import param

from matplotlib.axis import Axis

pn.extension('plotly')
pn.extension('tabulator', css_files=[pn.io.resources.CSS_URLS['font-awesome']])

# Loading pickles: Optional: We can either obtain the datasets in another python file and load them here via pickle
# !OR! put everything in this python file and not use pickles.
with open('df_nat_gas_ru.pickle', 'rb') as handle:
    df_gas = pickle.load(handle)
with open('df_oil_petrol_ru.pickle', 'rb') as handle:
    df_oil = pickle.load(handle)
with open('df_solid_fuel_ru.pickle', 'rb') as handle:
    df_solid = pickle.load(handle)
with open('gdf.pickle', 'rb') as handle:
    gdf = pickle.load(handle)
with open('df_natural_gas_exporters.pickle', 'rb') as handle:
    df_gas_treemap = pickle.load(handle)
with open('df_oil_petrol_exporters.pickle', 'rb') as handle:
    df_oil_treemap = pickle.load(handle)
with open('df_solid_fuel_exporters.pickle', 'rb') as handle:
    df_solid_treemap = pickle.load(handle)
gdf.crs = {"init": "epsg:4326"}

# Getting a list of countries:
countries = list(df_gas['Country'].unique())
dropdown_country = pn.widgets.Select(name='Select', options=countries, width=130, margin=(-5, 0, 0, 0))


def get_dataset(name, year=None):
    """ This handle function is called when a specific sub-dataset for the map is required based on the year chosen
    and the current global datasetname.
    :param name: name of the energy import dataset to pass
    :param year: chosen
    year to filter the dataset on
    :return: filtered dataset merged with the countries' polygons dataset
    """
    global datasetname, units
    if name == "Natural Gas":
        df = df_gas[df_gas['Year'] == year]
        units = 'million m3'
    elif name == "Oil Petrol":
        df = df_oil[df_oil['Year'] == year]
        units = 'thousand tonnes'
    elif name == "Solid Fuel":
        df = df_solid[df_solid['Year'] == year]
        units = 'thousand tonnes'
    datasetname = name
    merged = gdf.merge(df, on='Country', how='left')
    return merged


def get_dataset_exp(name, year, country='EU27_2020'):
    """This handle function is called when a specific sub-dataset for the treemap is required based on the year chosen,
    the current global datasetname, and the country selected.
    :param name: name of the energy import dataset to pass
    :param year: chosen year to filter the dataset on
    :param country: country chosen to filter the dataset on
    :return: filtered dataset based on the
    """
    global datasetname, units
    if name == "Natural Gas":
        df = df_gas_treemap[df_gas_treemap['Country'] == country]
        df = df[df['Year'] == year].round(1)
        units = 'million m3'
    elif name == "Oil Petrol":
        df = df_oil_treemap[df_oil_treemap['Country'] == country]
        df = df[df['Year'] == year].round(1)
        units = 'thousand tonnes'
    elif name == "Solid Fuel":
        df = df_solid_treemap[df_solid_treemap['Country'] == country]
        df = df[df['Year'] == year].round(1)
        units = 'thousand tonnes'

    df = df[df['Import'] != 0]
    datasetname = name
    return df


def get_dataset_line(name, year, country='EU27_2020'):
    """ This handle function is called when a specific sub-dataset for the line graph is required based on the year
    chosen, the current global datasetname, and the country selected.
    :param name: name of the energy import dataset to pass
    :param year: chosen year to filter the dataset on
    :param country: country chosen to filter the dataset on
    :return: filtered dataset based on the
    """
    global datasetname
    global units
    if name == "Natural Gas":
        df = df_gas[df_gas['Country'] == country].round(1)
        units = 'million m3'
        # df = df[df['Year'] == year]
    elif name == "Oil Petrol":
        df = df_oil[df_oil['Country'] == country].round(1)
        units = 'thousand tonnes'
        # df = df[df['Year'] == year]
    elif name == "Solid Fuel":
        df = df_solid[df_solid['Country'] == country].round(1)
        units = 'thousand tonnes'
        # df = df[df['Year'] == year]

    datasetname = name
    return df


datasetname = 'Natural Gas'
units = 'm3'
sel_country = 'EU27_2020'
year = 2020


# Ref: https://dmnfarrell.github.io/bioinformatics/bokeh-maps
def get_geodatasource(gdf):
    """Get getjsondatasource from geopandas object"""
    json_data = json.dumps(json.loads(gdf.to_json()))
    return GeoJSONDataSource(geojson=json_data)


# Define custom tick labels for color bar.
tick_labels = {'0': '0%', '20': '20%', '40': '40%', '60': '60%', '80': '80%', '100': '100%', }

replot = False


def selected_country(attr, old, new):
    """ This is a callback function that is called upon a map click. It allows highlighting the clicked country on
    the map.
    :param attr:
    :param old: old clicked value
    :param new: the most recent clicked value
    :return: None
    """
    global sel_country, replot
    sel_country = gdf._get_value(new[0], 'Country')
    if sel_country in countries:
        dropdown_country.value = sel_country
    else:
        replot = True
        dropdown_country.value = 'Poland'
        # dropdown_country.value = 'None'  # This is here to fake the change if two consecutive countries are out of
        # list
        dropdown_country.value = 'EU27_2020'


# Ref: https://dmnfarrell.github.io/bioinformatics/bokeh-maps
def bokeh_plot_map(gdf, column=None):
    """ Function plotting the bokeh map from GeoJSONDataSource and returning the map plot figure.

    :param gdf: input of the geosource data
    :param column: chosen name of the column to be filtered
    :return: map figure
    """
    global datasetname
    geosource = get_geodatasource(gdf)
    geosource.selected.on_change('indices', selected_country)
    if replot is False:
        geosource.selected.indices = gdf.index[gdf['Country'] == sel_country].tolist()
    if datasetname == "Natural Gas":
        palette = brewer['Greens'][8]
    elif datasetname == "Oil Petrol":
        palette = brewer['Blues'][8]
    elif datasetname == "Solid Fuel":
        palette = brewer['Oranges'][8]
    palette = palette[::-1]
    vals = gdf[column]

    hover_custom = HoverTool(tooltips=[('Country', '@Country'),
                                       ('Russian {} Import'.format(datasetname), '@Import{0.0} %')])
    # Instantiate LinearColorMapper that linearly maps numbers in a range, into a sequence of colors.
    color_mapper = LinearColorMapper(palette=palette, low=0, high=100)
    color_bar = ColorBar(color_mapper=color_mapper, label_standoff=8, height=660, width=20,
                         location=(0, 0), orientation='vertical', border_line_color=None,
                         major_label_overrides=tick_labels, background_fill_color='WhiteSmoke')

    tools = 'wheel_zoom,pan,reset,tap'
    p = figure(title='', plot_height=250, plot_width=600, toolbar_location='right', tools=tools)
    p.xaxis.visible = False
    p.yaxis.visible = False
    p.xgrid.grid_line_color = None
    p.ygrid.grid_line_color = None
    p.background_fill_color = (245, 245, 245)
    p.border_fill_color = (245, 245, 245)
    p.outline_line_color = (245, 245, 245)
    # Add patch renderer to figure
    p.patches('xs', 'ys', source=geosource, fill_alpha=1, line_width=0.5, line_color='black',
              fill_color={'field': column, 'transform': color_mapper})
    # Specify figure layout.
    p.add_layout(color_bar, 'right')
    p.add_tools(hover_custom)
    return p


# Ref: https://plotly.com/python/treemaps/
def plotly_plot_treemap(df, column=None, title=''):
    """ Function plotting the plotly treemap from the filtered dataset and returning the treemap plot figure.
    :param df: filtered dataset by country and year
    :param column: data column of the dataset to be displayed
    :param title: title of the figure
    :return: treemap figure
    """
    # Ref: https://discourse.bokeh.org/t/treemap-chart/7907/3
    p = px.treemap(df, path=['Continent', 'Partner'], values=column,
                   color='Import', hover_data=[column],
                   color_continuous_scale='Greys',
                   color_continuous_midpoint=np.average(df[column],
                                                        weights=df[column]))
    # print(df_treemap)
    p.update_layout(margin=dict(l=20, r=5, b=1, t=20, pad=5),
                    paper_bgcolor="WhiteSmoke")
    return p


def bokeh_plot_lines(df, column=None, year=None):
    """ Function plotting the bokeh line graph from the filtered dataset and returning the timeline plot figure.
    :param df: filtered dataset by country and year
    :param column: data column of the dataset to be displayed
    :param year: year to be used for drawing
    :return: plot lines graph figure
    """
    global datasetname
    if datasetname == "Natural Gas":
        color = 'green'
    elif datasetname == "Oil Petrol":
        color = 'blue'
    elif datasetname == "Solid Fuel":
        color = 'orange'

    source = ColumnDataSource(df)
    p = figure(x_range=(2000, 2020))
    p.line(x='Year', y=column, line_width=3, line_color=color, source=source, legend_label=df.iloc[0]['Country'])
    p.y_range = Range1d(start=0, end=110)
    p.yaxis.axis_label = 'Dependency on Russia in %'

    if year is not None:
        source = ColumnDataSource(df.loc[(df.Year == year)])
        p.vbar(x='Year', top=column, bottom=0, width=0.5, source=source, fill_color=color, fill_alpha=0.5)
    p.background_fill_color = (245, 245, 245)
    p.border_fill_color = (245, 245, 245)
    p.outline_line_color = (245, 245, 245)
    return p


# not used for now
def bokeh_plot_multilines(df, column=None, year=None):
    global datasetname
    if datasetname == "Natural Gas":
        color = 'green'
        df_main = df_gas
    elif datasetname == "Oil Petrol":
        color = 'blue'
        df_main = df_oil
    elif datasetname == "Solid Fuel":
        color = 'orange'
        df_main = df_solid

    source = ColumnDataSource(df)
    p = figure(x_range=(2000, 2020))
    p.line(x='Year', y=column, line_width=2, line_color=color, source=source, legend_label=df.iloc[0]['Country'])
    p.y_range = Range1d(0, 100, max_interval=100, min_interval=0)
    p.yaxis.axis_label = 'Dependency on Russia in %'

    for country in countries:
        p.line(x='Year', y=column, line_color='gray', source=ColumnDataSource())

    if year is not None:
        # df = df[df['Year'] == year]
        source = ColumnDataSource(df.loc[(df.Year == year)])
        p.vbar(x='Year', top=column, bottom=0, width=0.5, source=source, fill_color=color, fill_alpha=0.5)
    p.background_fill_color = "WhiteSmoke"
    return p


# ref.: https://stackoverflow.com/questions/57301630/trigger-event-on-mouseup-instead-of-continuosly-with-panel-slider-widget
class IntThrottledSlider(pnw.IntSlider):
    value_throttled = param.Integer(default=0)


map_pane = None


# Ref: https://dmnfarrell.github.io/bioinformatics/bokeh-maps
def create_app():
    """ Main function that is called, creating an app on bokeh server.
    :return: visualization application
    """
    map_pane = pn.pane.Bokeh(width=900, height=650)
    data_select = pn.widgets.RadioButtonGroup(name='Select Dataset',
                                              options=['Natural Gas', 'Oil Petrol', 'Solid Fuel'])
    year_slider = IntThrottledSlider(name='Year', start=2000, end=2020, callback_policy='mouseup', value=2020)
    dropdown_country.value = sel_country
    treemap_pane = pn.pane.plotly.Plotly(width=780, height=370, margin=(-8, 0, 0, 0))
    lines_pane = pn.pane.Bokeh(height=220, width=780, margin=(0, 50, 0, 0))

    df_table = pd.DataFrame(
        {'Country': [sel_country], 'Import Percentage (%)': [0], 'Import Value ({})'.format(units): [0]}).set_index(
        'Country')
    table_formatters = {
        '  Import Percentage (%)': NumberFormatter(format='0.0'),
        '  Import Value ({})'.format(units): NumberFormatter(format='0'),
    }
    table_pane = pn.widgets.Tabulator(df_table, name='DataFrame', disabled=True, formatters=table_formatters)

    def update_table():
        """ Function called by the application being run to update the parts of the visualizations.
        :return: None
        """
        global table_formatters
        df_treemap = get_dataset_exp(name=data_select.value, year=year_slider.value, country=dropdown_country.value)
        df_lines = get_dataset_line(name=data_select.value, year=year_slider.value, country=dropdown_country.value)
        country_rel = df_lines[(df_lines['Year'] == year_slider.value)].iat[0, 2]
        country_abs = df_treemap[(df_treemap['Partner'] == 'Russia')].iat[0, 4]
        table_formatters = {
            '  Import Percentage (%)': NumberFormatter(format='0.0'),
            '  Import Value ({})'.format(units): NumberFormatter(format='0'),
        }
        df_table = pd.DataFrame({'Country': [sel_country], 'Import Percentage (%)': [country_rel],
                                 'Import Value ({})'.format(units): [country_abs]}).set_index('Country')
        table_pane.value = df_table

    pn.state.add_periodic_callback(update_table, period=1000)

    def update_widgets(event):
        """ Function called by the application being run to update the parts of the visualizations.
        :return: None
        """
        global replot, sel_country
        sel_country = dropdown_country.value

        # replotting the map only if event is different from clicking on the country
        if str(event.obj)[:6] != 'Select' or replot is True:
            df_map = get_dataset(name=data_select.value, year=year_slider.value)
            map_pane.object = bokeh_plot_map(df_map, column='Import')
            # geosource.selected = Selection(indices=gdf.index[gdf['Country'] == sel_country].tolist())
            # if replot is False:
            #    geosource.selected.indices = gdf.index[gdf['Country'] == sel_country].tolist()
            replot = False

        df_treemap = get_dataset_exp(name=data_select.value, year=year_slider.value, country=dropdown_country.value)
        treemap_pane.object = plotly_plot_treemap(df_treemap, column='Import')

        df_lines = get_dataset_line(name=data_select.value, year=year_slider.value, country=dropdown_country.value)
        lines_pane.object = bokeh_plot_lines(df_lines, column='Import', year=year_slider.value)
        return

    year_slider.param.watch(update_widgets, 'value_throttled')
    year_slider.param.trigger('value_throttled')
    data_select.param.watch(update_widgets, 'value')
    dropdown_country.param.watch(update_widgets, 'value')
    table_pane

    treeTitle = pn.widgets.StaticText(name='Treemap', value='Exporters of the energy product for chosen region',
                                      align="end", margin=(0, 80, 0, 0))
    # treeTitle = pn.pane.Markdown(""" *Treemap. Influence of Countries over Regions in Energy Export* """, align="end", margin=(-10, 80, 0, 0))
    lineTitle = pn.widgets.StaticText(name='Timegraph', value='Energy product dependency on Russia over time',
                                      align="end",
                                      margin=(0, 80, 0, 0))
    # lineTitle = pn.pane.Markdown(""" *Timegraph. Historical Energy Import Data for Selected Country* """, align="end", margin=(-10, 80, 0, 0))
    mapTitle = pn.widgets.StaticText(name='Map', value='Energy product dependency on Russia', align="end",
                                     margin=(0, 80, 0, 0))
    # mapTitle = pn.pane.Markdown(""" *Map. Russian Energy Export Influence over Europe* """, align="end", margin=(-15, 80, 0, 0))
    tableTitle = pn.widgets.StaticText(name='Table', value='Energy product import of selected country', align="start",
                                       margin=(0, 0, 0, 170))
    sourceTitle = pn.widgets.StaticText(name='Source', value=' Eurostat', align="end",
                                        margin=(0, 80, 0, 0))
    # tableTitle = pn.pane.Markdown(""" *Table. Selected Country Energy Import* """, align="start", margin=(-15, 0, 0, 180))
    mainTitle = pn.pane.Markdown('### *DEPENDENCY OF EUROPEAN UNION ON ENERGY IMPORTS FROM RUSSIA*',
                                 background=(245, 245, 245), style={'font-family': "arial"}, align="end",
                                 margin=(0, 70, 0, 0))

    map_pane.sizing_mode = "stretch_both"
    lines_pane.sizing_mode = "stretch_both"

    # l = pn.Column(pn.Row(data_select, pn.Spacer(width=10), year_slider, pn.Spacer(width=10), dropdown_country,
    #                     background='WhiteSmoke'), map_pane, mapTitle, table_pane, tableTitle, background='WhiteSmoke')
    l = pn.Column(pn.Row(data_select, pn.Spacer(width=10), year_slider, pn.Spacer(width=10),
                         background='WhiteSmoke'), map_pane, mapTitle, table_pane, tableTitle, background='WhiteSmoke')
    # l.aspect_ratio = 1.2
    l.sizing_mode = "scale_both"
    l2 = pn.Column(mainTitle, treemap_pane, treeTitle, lines_pane, lineTitle, sourceTitle, background='WhiteSmoke')
    app = pn.Row(l, l2, background='WhiteSmoke')

    app.sizing_mode = "stretch_height"
    app.servable()
    return app


app = create_app()
