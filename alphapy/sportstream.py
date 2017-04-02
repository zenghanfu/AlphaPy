################################################################################
#
# Package   : AlphaPy
# Module    : sportstream
# Created   : July 11, 2013
#
# Copyright 2017 ScottFree Analytics LLC
# Mark Conway & Robert D. Scott II
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Example: sportstream -d './config'
#
################################################################################


#
# Imports
#

print(__doc__)

from alphapy.__main__ import main_pipeline
from alphapy.estimators import ModelType
from alphapy.frame import read_frame
from alphapy.frame import write_frame
from alphapy.globs import PSEP, SSEP, USEP
from alphapy.globs import WILDCARD
from alphapy.model import get_model_config
from alphapy.model import Model
from alphapy.space import Space

import argparse
import datetime
from itertools import groupby
import logging
import math
import numpy as np
import pandas as pd
import yaml


#
# Initialize logger
#

logger = logging.getLogger(__name__)


#
# Sports Fields
#
# The following fields are repeated for:
#     1. 'home'
#     2. 'away'
#     3. 'delta'
#
# Note that [Target]s will not be merged into the Game table;
# these targets will be predictors in the Game table that are
# generated after each game result. All of the fields below
# are predictors and are generated a priori, i.e., we calculate
# deltas from the last previously played game for each team and
# these data go into the row for the next game to be played.
#

sports_dict = {'wins' : int,
               'losses' : int,
               'ties' : int,
               'days_since_first_game' : int,
               'days_since_previous_game' : int,
               'won_on_points' : bool,
               'lost_on_points' : bool,
               'won_on_spread' : bool,
               'lost_on_spread' : bool,
               'point_win_streak' : int,
               'point_loss_streak' : int,
               'point_margin_game' : int,
               'point_margin_season' : int,
               'point_margin_season_avg' : float,
               'point_margin_streak' : int,
               'point_margin_streak_avg' : float,
               'point_margin_ngames' : int,
               'point_margin_ngames_avg' : float,
               'cover_win_streak' : int,
               'cover_loss_streak' : int,
               'cover_margin_game' : float,
               'cover_margin_season' : float, 
               'cover_margin_season_avg' : float,
               'cover_margin_streak' : float,
               'cover_margin_streak_avg' : float,
               'cover_margin_ngames' : float,
               'cover_margin_ngames_avg' : float,
               'total_points' : int,
               'overunder_margin' : float,
               'over' : bool,
               'under' : bool,
               'over_streak' : int,
               'under_streak' : int,
               'overunder_season' : float,
               'overunder_season_avg' : float,
               'overunder_streak' : float,
               'overunder_streak_avg' : float,
               'overunder_ngames' : float,
               'overunder_ngames_avg' : float}


#
# These are the leaders. Generally, we try to predict one of these
# variables as the target and lag the remaining ones.
#

game_dict = {'point_margin_game' : int,
             'won_on_points' : bool,
             'lost_on_points' : bool,
             'cover_margin_game' : float,
             'won_on_spread' : bool,
             'lost_on_spread' : bool,
             'overunder_margin' : float,
             'over' : bool,
             'under' : bool}


#
# Function get_game_config
#

def get_game_config(cfg_dir):
    r"""Read the configuration file for StockStream.

    Parameters
    ----------
    cfg_dir : str
        The directory where the configuration file ``market.yml``
        is stored.

    Returns
    -------
    specs : dict
        The parameters for controlling StockStream.

    """

    # Read the configuration file

    full_path = SSEP.join([cfg_dir, 'game.yml'])
    with open(full_path, 'r') as ymlfile:
        cfg = yaml.load(ymlfile)

    # Store configuration parameters in dictionary

    specs = {}

    # Section: game

    specs['points_max'] = cfg['game']['points_max']
    specs['points_min'] = cfg['game']['points_min']
    specs['predict_date'] = cfg['game']['predict_date']
    specs['random_scoring'] = cfg['game']['random_scoring']
    specs['rolling_window'] = cfg['game']['rolling_window']   
    specs['seasons'] = cfg['game']['seasons']
    specs['train_date'] = cfg['game']['train_date']

    # Log the game parameters

    logger.info('GAME PARAMETERS:')
    logger.info('points_max       = %d', specs['points_max'])
    logger.info('points_min       = %d', specs['points_min'])
    logger.info('predict_date     = %s', specs['predict_date'])
    logger.info('random_scoring   = %r', specs['random_scoring'])
    logger.info('rolling_window   = %d', specs['rolling_window'])
    logger.info('seasons          = %s', specs['seasons'])
    logger.info('train_date       = %s', specs['train_date'])

    # Game Specifications
    return specs


#
# Function get_point_margin
#

def get_point_margin(row, score, opponent_score):
    r"""Run an analysis for a given model and group

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    point_margin = 0
    nans = math.isnan(row[score]) or math.isnan(row[opponent_score])
    if not nans:
        point_margin = row[score] - row[opponent_score]
    return point_margin


#
# Function get_wins
#

def get_wins(point_margin):
    r"""Run an analysis for a given model and group

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    return 1 if point_margin > 0 else 0


#
# Function get_losses
#

def get_losses(point_margin):
    r"""Run an analysis for a given model and group

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    return 1 if point_margin < 0 else 0


#
# Function get_ties
#

def get_ties(point_margin):
    r"""Run an analysis for a given model and group

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    return 1 if point_margin == 0 else 0


#
# Function get_day_offset
#

def get_day_offset(date_vector):
    r"""Run an analysis for a given model and group

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    dv = pd.to_datetime(date_vector)
    offsets = pd.to_datetime(dv) - pd.to_datetime(dv[0])
    return offsets.astype('timedelta64[D]').astype(int)


#
# Function get_series_diff
#

def get_series_diff(series):
    r"""Run an analysis for a given model and group

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    new_series = pd.Series(len(series))
    new_series = series.diff()
    new_series[0] = 0
    return new_series


#
# Function get_streak
#

def get_streak(series, start_index, window):
    r"""Run an analysis for a given model and group

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    if window <= 0:
        window = len(series)
    i = start_index
    streak = 0
    while i >= 0 and (start_index-i+1) < window and series[i]:
        streak += 1
        i -= 1
    return streak


#
# Function add_features
#

def add_features(frame, fdict, flen, prefix=''):
    r"""Run an analysis for a given model and group

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    # generate sequences
    seqint = [0] * flen
    seqfloat = [0.0] * flen
    seqbool = [False] * flen
    # initialize new fields in frame
    for key, value in fdict.items():
        newkey = key
        if prefix:
            newkey = PSEP.join([prefix, newkey])
        if value == int:
            frame[newkey] = pd.Series(seqint)
        elif value == float:
            frame[newkey] = pd.Series(seqfloat)
        elif value == bool:
            frame[newkey] = pd.Series(seqbool)
        else:
            raise ValueError("Type to generate feature series not found")
    return frame


#
# Function generate_team_frame
#

def generate_team_frame(team, tf, home_team, away_team, window):
    r"""Run an analysis for a given model and group

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    # Initialize new features
    tf = add_features(tf, sports_dict, len(tf))
    # Daily Offsets
    tf['days_since_first_game'] = get_day_offset(tf['date'])
    tf['days_since_previous_game'] = get_series_diff(tf['days_since_first_game'])
    # Team Loop
    for index, row in tf.iterrows():
        if team == row[home_team]:
            tf['point_margin_game'].at[index] = get_point_margin(row, 'home.score', 'away.score')
            line = row['line']
        elif team == row[away_team]:
            tf['point_margin_game'].at[index] = get_point_margin(row, 'away.score', 'home.score')
            line = -row['line']
        else:
            raise KeyError("Team not found in Team Frame")
        if index == 0:
            tf['wins'].at[index] = get_wins(tf['point_margin_game'].at[index])
            tf['losses'].at[index] = get_losses(tf['point_margin_game'].at[index])
            tf['ties'].at[index] = get_ties(tf['point_margin_game'].at[index])
        else:
            tf['wins'].at[index] = tf['wins'].at[index-1] + get_wins(tf['point_margin_game'].at[index])
            tf['losses'].at[index] = tf['losses'].at[index-1] + get_losses(tf['point_margin_game'].at[index])
            tf['ties'].at[index] = tf['ties'].at[index-1] + get_ties(tf['point_margin_game'].at[index])
        tf['won_on_points'].at[index] = True if tf['point_margin_game'].at[index] > 0 else False
        tf['lost_on_points'].at[index] = True if tf['point_margin_game'].at[index] < 0 else False
        tf['cover_margin_game'].at[index] = tf['point_margin_game'].at[index] + line
        tf['won_on_spread'].at[index] = True if tf['cover_margin_game'].at[index] > 0 else False
        tf['lost_on_spread'].at[index] = True if tf['cover_margin_game'].at[index] <= 0 else False
        nans = math.isnan(row['home.score']) or math.isnan(row['away.score'])
        if not nans:
            tf['total_points'].at[index] = row['home.score'] + row['away.score']
        nans = math.isnan(row['over_under'])
        if not nans:
            tf['overunder_margin'].at[index] = tf['total_points'].at[index] - row['over_under']
        tf['over'].at[index] = True if tf['overunder_margin'].at[index] > 0 else False
        tf['under'].at[index] = True if tf['overunder_margin'].at[index] < 0 else False
        tf['point_win_streak'].at[index] = get_streak(tf['won_on_points'], index, 0)
        tf['point_loss_streak'].at[index] = get_streak(tf['lost_on_points'], index, 0)
        tf['cover_win_streak'].at[index] = get_streak(tf['won_on_spread'], index, 0)
        tf['cover_loss_streak'].at[index] = get_streak(tf['lost_on_spread'], index, 0)
        tf['over_streak'].at[index] = get_streak(tf['over'], index, 0)
        tf['under_streak'].at[index] = get_streak(tf['under'], index, 0)
        # Handle the streaks
        if tf['point_win_streak'].at[index] > 0:
            streak = tf['point_win_streak'].at[index]
        elif tf['point_loss_streak'].at[index] > 0:
            streak = tf['point_loss_streak'].at[index]
        else:
            streak = 1
        tf['point_margin_streak'].at[index] = tf['point_margin_game'][index-streak+1:index+1].sum()
        tf['point_margin_streak_avg'].at[index] = tf['point_margin_game'][index-streak+1:index+1].mean()
        if tf['cover_win_streak'].at[index] > 0:
            streak = tf['cover_win_streak'].at[index]
        elif tf['cover_loss_streak'].at[index] > 0:
            streak = tf['cover_loss_streak'].at[index]
        else:
            streak = 1
        tf['cover_margin_streak'].at[index] = tf['cover_margin_game'][index-streak+1:index+1].sum()
        tf['cover_margin_streak_avg'].at[index] = tf['cover_margin_game'][index-streak+1:index+1].mean()
        if tf['over_streak'].at[index] > 0:
            streak = tf['over_streak'].at[index]
        elif tf['under_streak'].at[index] > 0:
            streak = tf['under_streak'].at[index]
        else:
            streak = 1
        tf['overunder_streak'].at[index] = tf['overunder_margin'][index-streak+1:index+1].sum()
        tf['overunder_streak_avg'].at[index] = tf['overunder_margin'][index-streak+1:index+1].mean()
    # Rolling and Expanding Variables
    tf['point_margin_season'] = tf['point_margin_game'].cumsum()
    tf['point_margin_season_avg'] = tf['point_margin_game'].expanding().mean()
    tf['point_margin_ngames'] = tf['point_margin_game'].rolling(window=window, min_periods=1).sum()
    tf['point_margin_ngames_avg'] = tf['point_margin_game'].rolling(window=window, min_periods=1).mean()
    tf['cover_margin_season'] = tf['cover_margin_game'].cumsum()
    tf['cover_margin_season_avg'] = tf['cover_margin_game'].expanding().mean()
    tf['cover_margin_ngames'] = tf['cover_margin_game'].rolling(window=window, min_periods=1).sum()
    tf['cover_margin_ngames_avg'] = tf['cover_margin_game'].rolling(window=window, min_periods=1).mean()
    tf['overunder_season'] = tf['overunder_margin'].cumsum()
    tf['overunder_season_avg'] = tf['overunder_margin'].expanding().mean()
    tf['overunder_ngames'] = tf['overunder_margin'].rolling(window=window, min_periods=1).sum()
    tf['overunder_ngames_avg'] = tf['overunder_margin'].rolling(window=window, min_periods=1).mean()
    return tf


#
# Function get_team_frame
#

def get_team_frame(game_frame, team, home, away):
    r"""Extract only those games that involve a specific team.

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    team_frame = game_frame[(game_frame[home] == team) | (game_frame[away] == team)]
    return team_frame


#
# Function insert_model_data
#

def insert_model_data(mf, mpos, mdict, tf, tpos, prefix):
    r"""Run an analysis for a given model and group

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    team_row = tf.iloc[tpos]
    for key, value in mdict.items():
        newkey = key
        if prefix:
            newkey = PSEP.join([prefix, newkey])
        mf.at[mpos, newkey] = team_row[key]
    return mf


#
# Function generate_delta_data
#

def generate_delta_data(frame, fdict, prefix1, prefix2):
    r"""Run an analysis for a given model and group

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Parameters
    ----------
    var1 : array_like
        Array_like means all those objects -- lists, nested lists, etc. --
        that can be converted to an array.  We can also refer to
        variables like `var1`.
    var2 : int
        The type above can either refer to an actual Python type
        (e.g. ``int``), or describe the type of the variable in more
        detail, e.g. ``(N,) ndarray`` or ``array_like``.
    long_var_name : {'hi', 'ho'}, optional
        Choices in brackets, default first when optional.

    Returns
    -------
    type
        Explanation of anonymous return value of type ``type``.
    describe : type
        Explanation of return value named `describe`.
    out : type
        Explanation of `out`.

    Other Parameters
    ----------------
    only_seldom_used_keywords : type
        Explanation
    common_parameters_listed_above : type
        Explanation

    Raises
    ------
    BadException
        Because you shouldn't have done that.

    See Also
    --------
    otherfunc : relationship (optional)
    newfunc : Relationship (optional), which could be fairly long, in which
              case the line wraps here.
    thirdfunc, fourthfunc, fifthfunc

    Notes
    -----
    Notes about the implementation algorithm (if needed).

    This can have multiple paragraphs.

    You may include some math:

    .. math:: X(e^{j\omega } ) = x(n)e^{ - j\omega n}

    And even use a greek symbol like :math:`omega` inline.

    References
    ----------
    Cite the relevant literature, e.g. [1]_.  You may also cite these
    references in the notes section above.

    .. [1] O. McNoleg, "The integration of GIS, remote sensing,
       expert systems and adaptive co-kriging for environmental habitat
       modelling of the Highland Haggis using object-oriented, fuzzy-logic
       and neural-network techniques," Computers & Geosciences, vol. 22,
       pp. 585-588, 1996.

    Examples
    --------
    These are written in doctest format, and should illustrate how to
    use the function.

    >>> a = [1, 2, 3]
    >>> print [x + 3 for x in a]
    [4, 5, 6]
    >>> print "a\n\nb"
    a
    b

    """
    for key, value in fdict.items():
        newkey = PSEP.join(['delta', key])
        key1 = PSEP.join([prefix1, key])
        key2 = PSEP.join([prefix2, key])
        frame[newkey] = frame[key1] - frame[key2]
    return frame


#
# Function main
#

def main(args=None):
    r"""The main program for SportStream.

    Several sentences providing an extended description. Refer to
    variables using back-ticks, e.g. `var`.

    Notes
    -----
    (1) Initialize logging.
    (2) Parse the command line arguments.
    (3) Get the game configuration.

    (4) Get the model configuration.
    (5) Create the model object.
    (6) Call the main StockStream pipeline.

    """

    # Logging

    logging.basicConfig(format="[%(asctime)s] %(levelname)s\t%(message)s",
                        filename="sportstream.log", filemode='a', level=logging.DEBUG,
                        datefmt='%m/%d/%y %H:%M:%S')
    formatter = logging.Formatter("[%(asctime)s] %(levelname)s\t%(message)s",
                                  datefmt='%m/%d/%y %H:%M:%S')
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)

    logger = logging.getLogger(__name__)

    # Start the pipeline

    logger.info('*'*80)
    logger.info("START SportStream PIPELINE")
    logger.info('*'*80)

    # Argument Parsing

    parser = argparse.ArgumentParser(description="SportStream Parser")
    parser.add_argument("-d", dest="cfg_dir", default=".",
                        help="directory location of configuration files")
    parser.add_mutually_exclusive_group(required=False)
    parser.add_argument('--score', dest='scoring', action='store_true')
    parser.add_argument('--train', dest='scoring', action='store_false')
    parser.set_defaults(scoring=False)
    args = parser.parse_args()

    # Read game configuration file

    game_specs = get_game_config(args.cfg_dir)

    # Section: game

    points_max = game_specs['points_max']
    points_min = game_specs['points_min']
    predict_date = game_specs['predict_date']
    random_scoring = game_specs['random_scoring']
    seasons = game_specs['seasons']
    train_date = game_specs['train_date']
    window = game_specs['rolling_window']   

    # Read model configuration file

    specs = get_model_config(args.cfg_dir)
    specs['scoring'] = args.scoring

    # Unpack model arguments

    directory = specs['directory']
    organization = directory.split(SSEP)[-1]
    target = specs['target']

    # Create the game scores space

    space = Space('game', 'scores', '1g')

    #
    # Derived Variables
    #

    series = space.schema
    team1_prefix = 'home'
    team2_prefix = 'away'
    home_team = PSEP.join([team1_prefix, 'team'])
    away_team = PSEP.join([team2_prefix, 'team'])

    #
    # Read in the game frame. This is the feature generation phase.
    #

    logger.info("Reading Game Data")

    data_dir = SSEP.join([directory, 'data'])
    file_base = USEP.join([organization, space.subject, space.schema, space.fractal])
    df = read_frame(data_dir, file_base, specs['extension'], specs['separator'])
    logger.info("Total Game Records: %d", df.shape[0])

    #
    # Locate any rows with null values
    #

    null_rows = df.isnull().any(axis=1)
    null_indices = [i for i, val in enumerate(null_rows.tolist()) if val == True]
    for i in null_indices:
        logger.info("Null Record: %d on Date: %s", i, df.date[i])

    #
    # Set the training date and prediction date
    #

    train_date = train_date.strftime('%Y-%m-%d')
    predict_date = predict_date.strftime('%Y-%m-%d')

    #
    # Run the game pipeline on a seasonal loop
    #

    if not seasons:
        # run model on all seasons
        seasons = df['season'].unique().tolist()

    #
    # Initialize the final frame
    #

    ff = pd.DataFrame()

    #
    # Iterate through each season of the game frame
    #

    for season in seasons:

        # Generate a frame for each season

        gf = df[df['season'] == season]
        gf = gf.reset_index(level=0)

        # Generate derived variables for the game frame

        total_games = gf.shape[0]
        if random_scoring:
            gf['home.score'] = np.random.randint(points_min, points_max, total_games)
            gf['away.score'] = np.random.randint(points_min, points_max, total_games)
        gf['total_points'] = gf['home.score'] + gf['away.score']

        gf = add_features(gf, game_dict, gf.shape[0])
        for index, row in gf.iterrows():
            gf['point_margin_game'].at[index] = get_point_margin(row, 'home.score', 'away.score')
            gf['won_on_points'].at[index] = True if gf['point_margin_game'].at[index] > 0 else False
            gf['lost_on_points'].at[index] = True if gf['point_margin_game'].at[index] < 0 else False
            gf['cover_margin_game'].at[index] = gf['point_margin_game'].at[index] + row['line']
            gf['won_on_spread'].at[index] = True if gf['cover_margin_game'].at[index] > 0 else False
            gf['lost_on_spread'].at[index] = True if gf['cover_margin_game'].at[index] <= 0 else False
            gf['overunder_margin'].at[index] = gf['total_points'].at[index] - row['over_under']
            gf['over'].at[index] = True if gf['overunder_margin'].at[index] > 0 else False
            gf['under'].at[index] = True if gf['overunder_margin'].at[index] < 0 else False

        # Generate each team frame

        team_frames = {}
        teams = gf.groupby([home_team])
        for team, data in teams:
            team_frame = USEP.join([organization, team.lower(), series, str(season)])
            logger.info("Generating team frame: %s", team_frame)
            tf = get_team_frame(gf, team, home_team, away_team)
            tf = tf.reset_index(level=0)
            tf = generate_team_frame(team, tf, home_team, away_team, window)
            team_frames[team_frame] = tf

        # Create the model frame, initializing the home and away frames

        mdict = {k:v for (k,v) in sports_dict.items() if v != bool}
        team1_frame = pd.DataFrame()
        team1_frame = add_features(team1_frame, mdict, gf.shape[0], prefix=team1_prefix)
        team2_frame = pd.DataFrame()
        team2_frame = add_features(team2_frame, mdict, gf.shape[0], prefix=team2_prefix)
        frames = [gf, team1_frame, team2_frame]
        mf = pd.concat(frames, axis=1)

        # Loop through each team frame, inserting data into the model frame row
        #     get index+1 [if valid]
        #     determine if team is home or away to get prefix
        #     try: np.where((gf[home_team] == 'PHI') & (gf['date'] == '09/07/14'))[0][0]
        #     Assign team frame fields to respective model frame fields: set gf.at(pos, field)

        for team, data in teams:
            team_frame = USEP.join([organization, team.lower(), series, str(season)])
            logger.info("Merging team frame %s into model frame", team_frame)
            tf = team_frames[team_frame]
            for index in range(0, tf.shape[0]-1):
                gindex = index + 1
                model_row = tf.iloc[gindex]
                key_date = model_row['date']
                at_home = False
                if team == model_row[home_team]:
                    at_home = True
                    key_team = model_row[home_team]
                elif team == model_row[away_team]:
                    key_team = model_row[away_team]
                else:
                    raise KeyError("Team not found in Team Frame")            
                try:
                    if at_home:
                        mpos = np.where((mf[home_team] == key_team) & (mf['date'] == key_date))[0][0]
                    else:
                        mpos = np.where((mf[away_team] == key_team) & (mf['date'] == key_date))[0][0]
                except:
                    raise IndexError("Team/Date Key not found in Model Frame")
                # print team, gindex, mpos
                # insert team data into model row
                mf = insert_model_data(mf, mpos, mdict, tf, index, team1_prefix if at_home else team2_prefix)

        # Compute delta data 'home' - 'away'

        mf = generate_delta_data(mf, mdict, team1_prefix, team2_prefix)

        # Append this to final frame

        frames = [ff, mf]
        ff = pd.concat(frames)

    #
    # Split data into training and test data
    #

    new_train_frame = ff.loc[(ff.date >= train_date) & (ff.date < predict_date)]
    if len(new_train_frame) <= 1:
        raise ValueError("Training frame has length 1 or less")

    new_test_frame = ff.loc[ff.date >= predict_date]
    if len(new_test_frame) <= 1:
        raise ValueError("Test frame has length 1 or less")

    #
    # Rewrite with all the features to the train and test files
    #

    input_dir = SSEP.join([directory, 'input'])
    write_frame(new_train_frame, input_dir, specs['train_file'],
                specs['extension'], specs['separator'])
    write_frame(new_test_frame, input_dir, specs['test_file'],
                specs['extension'], specs['separator'])

    #
    # Create the model from specs, and run the pipeline
    #

    logger.info("Running Model")

    model = Model(specs)
    model = main_pipeline(model)

    # Complete the pipeline

    logger.info('*'*80)
    logger.info("END SportStream PIPELINE")
    logger.info('*'*80)


#
# MAIN PROGRAM
#

if __name__ == "__main__":
    main()
