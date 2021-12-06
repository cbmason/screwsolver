#!/usr/bin/env python

"""
visualizer.py

Graphing functions for a SYN results database

Note: All PEP8 warnings relating to using "is" instead of == are to be ignored, == does not work since pandas implements
its own boolean
"""

import logging
import pandas
import os

import plotly.graph_objs as go
import plotly.figure_factory as ff

from argparse import ArgumentParser
from cards import Rank
from database import DBInterface
from simulations import SimFirstPositionSimpleFull, DEFAULT_DB_NAME, DEFAULT_ITERS


DEFAULT_CSV_NAME = "data/SYNDB.csv"


def _check_for_data(db, data_table):
    """
    Helper function, if data_table exists then just return it, otherwise generate it from the DB
    :param db: SQLite database
    :param data_table: pandas dataframe
    :return: the data_table
    """
    if data_table is None:
        if db is None:
            raise ValueError("Must provide either database name or data table")
        # Generate data table if not given one
        else:
            logging.info("No data passed to graph_x_player_winrate_by_start, generating table from DB...")
            data_table = generate_win_by_start_table(db)
    return data_table


def generate_win_by_start_table(dbfile, serialize=True):

    """
    Given a database of results, generate a pandas dataframe of win % consisting of:
    {int num players, int start card, boolean swap, float winrate}
    :param dbfile: file name of SQLite database
    :param serialize: whether to write out to .csv or not
    :return: the output pandas dataframe
    """
    output = pandas.DataFrame(columns=['num_players', 'start_card', 'swap', 'winrate'])
    database = DBInterface(dbfile)
    for i in range(2, 51):
        if database.get_does_player_count_exist(i):
            for card in range(Rank.Ace.value, Rank.King.value):
                print(f"Generating {i} player with {card} winrate when KEEPING")
                winratio = database.get_win_ratio_when_acting_first(i, card, True)
                winpct = winratio * 100
                output = output.append({'num_players': i, 'start_card': card, 'swap': True, 'winrate': winpct}, ignore_index=True)
                print(f"Generating {i} player with {card} winrate when PASSING")
                winratio = database.get_win_ratio_when_acting_first(i, card, False)
                winpct = winratio * 100
                output = output.append({'num_players': i, 'start_card': card, 'swap': False, 'winrate': winpct}, ignore_index=True)

    if serialize:
        # do the serialization
        filename = os.path.splitext(dbfile)[0] + ".csv"
        output.to_csv(filename, index=False)

    return output


def graph_x_player_winrate_by_start(num_players, db=None, data_table=None):
    """
    Given a number of players and either a table of player/card/winrate, draw a Plotly graph where x = card y = winrate,
    and there are two lines: one for keep and one for swap
    :param num_players: self-explanatory
    :param db: the SQLite database to use, only will be used as backup to generate a data_table if no data_table is
        provided
    :param data_table: pandas dataframe containing the data to graph
    :return: the data_table used or generated
    """

    data_table = _check_for_data(db, data_table)

    # Get rows where num_players = num_players
    graph_data = data_table.loc[data_table['num_players'] == num_players]

    # Draw the plotly graph
    trace1 = go.Scatter(
        x=graph_data[graph_data['swap'] == True].start_card,
        y=graph_data[graph_data['swap'] == True].winrate,
        mode="lines+markers",
        name="Pass",
        marker=dict(color='rgba(67,67,67,1.0)', ),
        line=dict(color='rgba(67,67,67,1.0)', width=2),
        text=[Rank(n) for n in Rank]
    )
    trace2 = go.Scatter(
        x=graph_data[graph_data['swap'] == False].start_card,
        y=graph_data[graph_data['swap'] == False].winrate,
        mode="lines+markers",
        name="Keep",
        # marker=dict(color='rgba(80, 26, 80, 0.8)'),
        marker=dict(color='rgba(67,67,67,0.5)'),
        line=dict(color='rgba(67,67,67,0.5)', width=3),
        text=[Rank(n) for n in Rank],
        connectgaps=True
    )

    layout = dict(title=f'Screw Your Neighbor first to act win rate by card rank ({num_players} players)',
                  xaxis=dict(title='Card Rank', ticklen=1, zeroline=False, width=1000, height=800))
    fig = go.Figure()
    fig.add_trace(trace1)
    fig.add_trace(trace2)
    fig.update_layout(layout)
    fig.show()

    return fig


def graph_all_players_winrate_by_start(db=None, data_table=None):
    """
    Draw a Plotly graph where x = card y = winrate, and there are two lines for each playercount in the data: one for
    keep and one for swap
    :param db: the SQLite database to use, only will be used as backup to generate a data_table if no data_table is
        provided
    :param data_table: pandas dataframe containing the data to graph
    :return: the data_table used or generated
    """

    data_table = _check_for_data(db, data_table)

    # master graph layout
    layout = dict(title=r'Screw Your Neighbor first to act win rate by card rank',
                  xaxis=dict(title='Card Rank', ticklen=1, zeroline=False),
                  yaxis=dict(title='Winrate (in %)', ticklen=1), legend_title_text='Playercount, Action',
                  width=1000, height=800)
    fig = go.Figure()
    fig.update_layout(layout)

    # for loop thru the colors / numbers
    index = 0
    playercounts = data_table.num_players.unique()
    counts_count = len(playercounts)
    for num_players in playercounts:
        # Get rows where num_players = num_players
        graph_data = data_table.loc[data_table['num_players'] == num_players]
        light_string = f'hsv({int(index * 100 / counts_count)}%, 100%, 100%)'
        dark_string = f'hsv({int(index * 100 / counts_count)}%, 50%, 100%)'

        # Draw the Pass graph
        trace1 = go.Scatter(
            x=graph_data[graph_data['swap'] == True].start_card,
            y=graph_data[graph_data['swap'] == True].winrate,
            mode="lines+markers",
            name=f"{num_players}, Pass",
            marker=dict(color=light_string, size=15),
            line=dict(color=light_string, width=4),
            text=[Rank(n) for n in Rank],
        )
        # Draw the Keep graph
        trace2 = go.Scatter(
            x=graph_data[graph_data['swap'] == False].start_card,
            y=graph_data[graph_data['swap'] == False].winrate,
            mode="lines+markers",
            name=f"{num_players}, Keep",
            marker=dict(color=dark_string, size=8),
            line=dict(color=dark_string, width=4, dash="dash"),
            text=[Rank(n) for n in Rank],
            connectgaps=True,
        )
        fig.add_trace(trace1)
        fig.add_trace(trace2)
        index += 1

    # Turn on the graph
    fig.show()
    return fig


def generate_heatmap(db=None, data_table=None):
    """
    The "most useful" (according to me) visualization: 2D graph of the optimal play given number of players and card
    you're holding.
    :param db: the SQLite database to use, only will be used as backup to generate a data_table if no data_table is
        provided
    :param data_table: pandas dataframe containing the data to graph
    :return: the data_table used or generated
    """
    data_table = _check_for_data(db, data_table)

    def _get_keep_winrate(data, card, players):
        keep_rate = data[(data['swap'] == False) &
                         (data['num_players'] == players) &
                         (data['start_card'] == card)].winrate.values[0]
        return keep_rate

    def _get_swap_winrate(data, card, players):
        swap_rate = data[(data['swap'] == True) &
                         (data['num_players'] == players) &
                         (data['start_card'] == card)].winrate.values[0]
        return swap_rate

    def _calc_prob_diff(data, card, players):
        swap_rate = _get_swap_winrate(data, card, players)
        keep_rate = _get_keep_winrate(data, card, players)
        return swap_rate - keep_rate

    def _label_swap_keep(swap_minus_keep):
        if swap_minus_keep > 0.0:
            return "Swap"
        else:
            return "Keep"

    def _label_winrates(data, card, players):
        swap_rate = _get_swap_winrate(data, card, players)
        keep_rate = _get_keep_winrate(data, card, players)
        return f"Swap: {swap_rate:.4}%, Keep: {keep_rate:.4}%"

    # get set of recorded player counts
    player_counts = data_table.num_players.unique()
    # max card is always the same, no need to do retrieve
    y = [str(cnt) for cnt in player_counts]
    z = [[_calc_prob_diff(data_table, card, players) for card in range(1, 13)] for players in player_counts]
    z_text = [[_label_swap_keep(x) for x in line] for line in z]
    mouseover_text = [[_label_winrates(data_table, card, players)
                       for card in range(1, 13)] for players in player_counts]

    # Plotly does not have a builtin red-green colorscale, so make one.
    red_green_scale = \
        (
            (0.0, 'rgb(103,0,31)'),
            (0.1, 'rgb(178,24,43)'),
            (0.2, 'rgb(214,96,77)'),
            (0.3, 'rgb(244,165,130)'),
            (0.4, 'rgb(253,219,199)'),
            (0.5, 'rgb(247,247,247)'),
            (0.6, 'rgb(209,240,229)'),
            (0.7, 'rgb(146,222,197)'),
            (0.8, 'rgb(67,195,147)'),
            (0.9, 'rgb(33,172,102)'),
            (1.0, 'rgb(5,97,48)')
        )

    fig = ff.create_annotated_heatmap(
        x=['A', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'J', 'Q'],
        # y=y,
        y=['two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'],
        z=z,
        annotation_text=z_text,
        hoverongaps=False,
        colorscale=red_green_scale,
        zmid=0,
        font_colors=['black'],
        text=mouseover_text
    )
    layout = dict(title={'text': r'Screw Your Neighbor *Swap - Keep* Win percentage',
                         'xanchor': 'auto',
                         'xref': 'container',
                         'yref': 'container',
                         'x': 0.5},
                  xaxis=dict(title='Card Rank', ticklen=1, zeroline=False),
                  yaxis=dict(title='Player Count', ticklen=1), legend_title_text='Playercount, Action',
                  showlegend=True, width=1200, height=800)
    fig.update_layout(layout)
    fig.update_xaxes(side="bottom")
    fig.show()
    return fig


def main(viz_type="heatmap", db=DEFAULT_DB_NAME, csv=DEFAULT_CSV_NAME, max_players=10, runs=DEFAULT_ITERS, image=None, html=None, force_regen=False):
    """Main function of the visualizer.

    Args:
        viz_type (str): "heatmap" or "lines, or lines_all" the two different visualizations currently implemented. Defaults to "heatmap".
        db (path, optional): Path to database to use. Defaults to {DEFAULT_DB_NAME}.
        csv (path, optional): Path to csv containing Pandas datatable to use. Defaults to {DEFAULT_CSV_NAME}.
        max_players (int, optional): Table size. Defaults to 10.
        runs (int, optional): Number of iterations. Defaults to the simulations.py module's default.
        image (path, optional): Outputs a .jpg of the results to this path. Defaults to None.
        html (path, optional): Outputs a .html of the results to this path. Defaults to None.
        force_regen (boolean, optional): Overwrites the given .csv file if True

    """

    # See if we have DB, CSV, or neither
    db_found = False
    csv_found = False
    # Check for CSV first, if that doesn't exist, check for DB
    if force_regen or not os.path.exists(csv):
        if not os.path.exists(db):
            print(f"No valid database or .csv file provided!  Running full spectrum sims to create database. \
                  Press Ctrl+C to cancel")
            for lowest in range(1, 14):
                print(f"Running full spectrum sim with {max_players} tablesize, keeping {lowest} and above")
                sim = SimFirstPositionSimpleFull(max_players, Rank(lowest), dbname=db, num_of_iters=runs)
                sim.run(consoleprint=True)
                sim.print_results()
            db_found = True
        # no CSV, but found a DB
        else:
            db_found = True
    else:
        # found a CSV, deserialize and use that
        data_from_file = pandas.read_csv(csv)
        csv_found = True

    # do heatmap
    if viz_type.lower() == 'heatmap':
        if csv_found:
            fig = generate_heatmap(data_table=data_from_file)
        elif db_found:
            fig = generate_heatmap(db=db)
        else:
            raise ValueError(f"No valid database or .csv file provided!")
        if html is not None:
            outfile_name = html + '.html'
            fig.write_html(outfile_name)
        if image is not None:
            outfile_name = image + '.png'
            fig.write_image(outfile_name)

    elif viz_type.lower() == 'lines_all':
        if csv_found:
            fig = graph_all_players_winrate_by_start(data_table=data_from_file)
        elif db_found:
            fig = graph_all_players_winrate_by_start(db=db)
        else:
            raise ValueError(f"No valid database or .csv file provided!")
        if html is not None:
            outfile_name = html + '.html'
            fig.write_html(outfile_name)
        if image is not None:
            outfile_name = image + '.png'
            fig.write_image(outfile_name)

    # do line graph with one or all
    else:
        # Check for invalid command
        if max_players < 2 or max_players > 51:
            raise ValueError(f"{max_players} is not a valid player count")

        else:
            if csv_found:
                fig = graph_x_player_winrate_by_start(max_players, data_table=data_from_file)
            elif db_found:
                fig = graph_x_player_winrate_by_start(max_players, db=db)
            else:
                raise ValueError(f"No valid database or .csv file provided!")
            if html is not None:
                outfile_name = html + '.html'
                fig.write_html(outfile_name)
            if image is not None:
                outfile_name = image + '.png'
                fig.write_image(outfile_name)


if __name__ == '__main__':
    """command line script"""
    parser = ArgumentParser(description='Transform a database or CSV list of game results into a set of graphs')
    parser.add_argument('type', choices=['heatmap', 'lines', 'lines_all'], default='heatmap', nargs='?')
    parser.add_argument('--db', default=DEFAULT_DB_NAME)
    parser.add_argument('--csv', default=DEFAULT_CSV_NAME)
    parser.add_argument('-p', '--players', type=int, default=10,
                        help="Max player count")
    parser.add_argument('-r', '--runs', type=int, default=100000,
                        help="Only used if we have to generate a DB.  Sim iterations run per strategy")
    parser.add_argument('-i', '--image', type=str, help="Output image file")
    parser.add_argument('-o', '--output', type=str, help="Output HTML file")
    parser.add_argument('-f', '--force', type=str, help="Forces regeneration of the .csv file")
    args = parser.parse_args()

    main(
        viz_type=args.type,
        db=args.db,
        csv=args.csv,
        max_players=args.players,
        runs=args.runs,
        image=args.image,
        html=args.output,
        force_regen=args.force
        )
