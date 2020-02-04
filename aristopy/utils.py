#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
** Utility functions **

* Last edited: 2020-01-01
* Created by: Stefan Bruche (TU Berlin)
"""
import warnings
import pandas as pd
import numpy as np
import pyomo.environ as pyomo
import aristopy


def aggregate_time_series(full_series, number_of_time_steps_to_aggregate,
                          aggregate_by='sum'):
    """
    Function to compress the original (full scale) time series to a shorter one.
    Returns an array with aggregated values. For aggregation the values can
    either be summed up ('sum') or averaged ('mean').
    (E.g. s = aggregate_time_series([1, 2, 3, 4], 2, 'sum') >> s = [3, 7]

    :param full_series: Original (full scale) hourly time series to aggregate.
        E.g. two time steps (hours) are summed up or averaged and handled as one
    :type full_series: pandas Series or numpy array or list

    :param number_of_time_steps_to_aggregate: Number of time steps to aggregate.
        Should be an integer divisor of the length of the full series.
    :type number_of_time_steps_to_aggregate: integer

    :param aggregate_by: aggregation method to apply. Can either be 'sum'
        (values are summed up) or 'mean' (values are averaged).
    :type aggregate_by: string ('sum' or 'mean')
    """
    # Check the user input:
    if not (isinstance(full_series, pd.Series) or isinstance(
            full_series, np.ndarray) or isinstance(full_series, list)):
        raise ValueError('The "full_series" can either by a pandas Series or a '
                         'numpy ndarray or a Python list.')
    is_strictly_positive_int(number_of_time_steps_to_aggregate)
    if not (aggregate_by == 'sum' or aggregate_by == 'mean'):
        raise ValueError('Keyword "aggregate_by" can either be "sum" or "mean"')

    # Check that number_of_time_steps_to_aggregate is an integer divisor of len
    if len(full_series) % number_of_time_steps_to_aggregate != 0:
        raise ValueError('The provided series can not be equally dived with '
                         'length {}'.format(number_of_time_steps_to_aggregate))
    else:
        # convert input to numpy array and reshape it e.g. [[1, 2] [3, 4], ...]
        s = np.array(full_series).reshape(-1, number_of_time_steps_to_aggregate)
        if aggregate_by == 'sum':
            # sum everything over axis 1 (horizontal) -> [3 7]
            s = s.sum(1)
        else:  # aggregate_by == 'mean'
            # calculate mean over axis 1 -> [1.5 3.5]
            s = s.mean(1)
        return s


def check_logger_input(logfile, delete_old, default_handler, local_handler,
                       default_level, local_level, screen_to_log):

    is_string(logfile), is_boolean(delete_old), is_boolean(screen_to_log)

    if default_handler not in ['file', 'stream']:
        raise ValueError('Input argument should be "file" or "stream".')

    if default_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        raise ValueError('Options for logger levels are: "DEBUG", "INFO", '
                         '"WARNING", "ERROR", "CRITICAL"')

    for key, val in local_handler.items():
        if key not in ['EnergySystemModel', 'Source', 'Sink', 'Conversion',
                       'Storage', 'Bus']:
            raise ValueError('Keys for dictionary "local_log_handler" are: '
                             '"EnergySystemModel", "Source", "Sink", '
                             '"Conversion", "Storage", "Bus"')
        if val not in ['file', 'stream']:
            raise ValueError('Input argument should be "file" or "stream".')

    for key, val in local_level.items():
        if key not in ['EnergySystemModel', 'Source', 'Sink', 'Conversion',
                       'Storage', 'Bus']:
            raise ValueError('Keys for dictionary "local_log_level" are: '
                             '"EnergySystemModel", "Source", "Sink", '
                             '"Conversion", "Storage", "Bus"')
        if val not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError('Options for logger levels are: "DEBUG", "INFO", '
                             '"WARNING", "ERROR", "CRITICAL"')


def set_if_positive(data):
    """  Check the input data for positivity and return the value. """
    # type float or integer and data >= 0.
    is_positive_number(data)
    return data

def set_if_between_zero_and_one(data):
    """  Check the input data for positivity and value less or equal one. """
    # type float or integer and data >= 0.
    is_positive_number(data)
    if not data <= 1:
        raise ValueError('The maximal value if the input argument is "1".')
    return data


def check_add_variable(name, domain, has_time_set, alternative_set, ub, lb):
    """ Check the user input of the function 'add_variable' that can be used to
        manually add variables to the main model instance. """
    is_string(name)
    if domain not in ['Binary', 'NonNegativeReals', 'Reals']:
        raise TypeError('Select the domain of the variable from "Binary", '
                        '"NonNegativeReals", "Reals"')
    is_boolean(has_time_set)
    if alternative_set is not None and not hasattr(alternative_set, '__iter__'):
        raise TypeError('The "alternative_set" keyword requires a iterable '
                        'Python object!')
    if ub is not None:
        is_number(ub)
    if lb is not None:
        is_number(lb)


def is_dataframe(data):
    if not isinstance(data, pd.DataFrame):
        raise TypeError('The data needs to be imported as a pandas DataFrame!')


def is_series(data):
    if not isinstance(data, pd.Series):
        raise TypeError('The data needs to be imported as a pandas Series!')


def check_add_constraint(name, has_time_set, alternative_set, rule):
    """ Check the user input for the function 'add_constraint' that can be used
        to manually add constraints to the main model instance. """
    if name is not None:
        is_string(name)
    is_boolean(has_time_set)
    if alternative_set is not None and not hasattr(alternative_set, '__iter__'):
        raise TypeError('The "alternative_set" keyword requires a iterable '
                        'Python object!')
    if not callable(rule):
        raise TypeError('The "rule" keyword needs to hold a callable object!')


def check_and_set_scalar_or_time_series(ensys, data):
    """ XXX """
    scalar, time_series = None, None  # init
    if data is not None:
        if isinstance(data, float) or isinstance(data, int):
            is_positive_number(data)  # raise error if value not >= 0
            scalar = data
        else:
            time_series = check_and_convert_time_series(ensys, data)
    return scalar, time_series


def check_and_set_capacities(cap, cap_min, cap_max, cap_per_mod, max_mod_nbr):
    """  Check input values for capacity arguments. """

    # positive floats or integers if not None
    for val in [cap, cap_min, cap_max, cap_per_mod, max_mod_nbr]:
        if val is not None:
            is_positive_number(val)

    # fixed capacity dominates other arguments
    if cap is not None:
        for val in [cap_min, cap_max, cap_per_mod, max_mod_nbr]:
            if val is not None:
                warnings.warn('Fixed capacity value "capacity" is specified. '
                              'Hence, parameters "capacity_min, capacity_max, '
                              'capacity_per_module, maximal_module_number" are '
                              'not required and ignored.')
        cap_min, cap_max = cap, cap  # cap_min = cap_max = cap
        cap_per_mod, max_mod_nbr = None, None

    # if fixed capacities are used (cap_min = cap_max) set cap to the same value
    if cap_min == cap_max and cap is None:
        cap = cap_min

    # raise an error if cap_min is larger than cap_max
    if cap_min is not None and cap_max is not None and cap_min > cap_max:
        raise ValueError('The minimal capacity of a component cannot exceed its'
                         ' maximal capacity!')

    # calculate cap_max from cap_per_mod and max_mod_nbr if needed and possible
    if cap_per_mod and max_mod_nbr is not None and cap_max is None:
        cap_max = cap_per_mod * max_mod_nbr

    # "maximal_module_number" is useless without "capacity_per_module" --> raise
    if cap_per_mod is None and max_mod_nbr is not None:
        raise ValueError('Please specify a value for the "capacity_per_module" '
                         'if you set a value for "maximal_module_number".')

    # Prevent invalid parameter combination and calculate max_mod_nbr if needed
    if cap_per_mod is not None and max_mod_nbr is None:
        if cap_max is None:
            raise ValueError('Cannot work with this combination of arguments. '
                             'If a value for  the "capacity_per_module" is set,'
                             ' an additional value for "maximal_module_number"'
                             ' or "capacity_max" is required.')
        else:
            max_mod_nbr = cap_max // cap_per_mod  # round down!

    return cap, cap_min, cap_max, cap_per_mod, max_mod_nbr


def check_operation_rates(comp, rate_min, rate_max, rate_fix):
    """  Check input values for operation rate arguments. """
    # Show warning if rate_fix is specified and rate_min or rate_max as well.
    # --> set rate_min and rate_max to None.
    if rate_fix is not None and (rate_min or rate_max is not None):
        rate_min, rate_max = None, None
        warnings.warn('\nIf "operation_rate_fix" is specified, the time series '
                      '"operation_rate_min" and "operation_rate_max" are not '
                      'required and are set to None.')

    # Names are strings (if not None)
    # Raise error if an operation_rate is specified and its name is not in the
    # 'parameters' dictionary of the component (if not None)
    for rate in [rate_min, rate_max, rate_fix]:
        check_existence_in_dataframe(rate, comp.parameters)
    # Raise error if min is larger than max at a certain position in the series
    if rate_min and rate_max is not None and (
            comp.parameters[rate_min]['full_resolution'] >
            comp.parameters[rate_max]['full_resolution']).all():
        raise ValueError('The series "operation_rate_min" has at least one '
                         'value that is larger than "operation_rate_max".')
    return rate_min, rate_max, rate_fix


def check_existence_in_dataframe(name, df):
    """ Raise an error if a name is not in the columns of a pandas DataFrame """
    if name is not None:
        is_string(name)
        if name not in df.columns:
            raise ValueError('Cannot find an attribute with the name "{}" in '
                             'the DataFrame. Available names are: {}.'
                             .format(name, list(df.columns)))
    return name


def check_inlets_and_outlets(data):
    """ The inlet and outlet attributes need to be of type dict. If a single
    string is given as key value, it is converted to a list with length 1. """
    if data is not None:
        if not isinstance(data, dict):
            raise ValueError('The "inlets" and "outlets" needs to be '
                             'dictionaries!')
        for key, val in data.items():
            if isinstance(val, str):
                data[key] = [val]  # to list
            if not isinstance(key, str):
                raise TypeError('Dictionary keys need to be of type string.')
    return data


def check_and_convert_to_list(value):
    """ Value should be of type list or a string that can be converted to a
    single string in a list of length 1. """
    if isinstance(value, str):
        return [value]
    elif isinstance(value, list):
        return value
    else:
        raise TypeError('The type of input "{}" should be a list or a single '
                        'string.'.format(value))


def check_user_dict(name, user_dict):
    if not isinstance(user_dict, dict):
        raise ValueError('"{}" needs to be a dictionary!'.format(name))
    for key, val in user_dict.items():
        if not isinstance(key, str):
            raise TypeError('Check "{}". Keys need to be strings!'.format(name))
        is_number(val)  # type is int or float


def check_and_convert_time_series(ensys, data):
    """
    Compare the length of the data with the time indices of the energy
    system model. And make sure the data is available as indexed pandas series.
    """
    #  If length of data is not sufficient raise an error
    if len(data) < len(ensys.total_time_steps):
        raise ValueError('The length of a time series is not sufficient for the'
                         ' number of time steps of the energy system model.\n'
                         'Time steps energy system model: {}\nLength data: {}\n'
                         'Data: {}'.format(len(ensys.total_time_steps),
                                           len(data), data))

    # Convert to pandas Series if data is in a dictionary (cannot slice dicts)
    if isinstance(data, dict):
        data = pd.Series(data)

    # If length of data is more than needed -> shorten the data, discard rest
    if len(data) > len(ensys.total_time_steps):
        data = data[:len(ensys.total_time_steps)]

    # Lists and arrays don't have an index --> add the time index of ensys
    if isinstance(data, list) or isinstance(data, np.ndarray):
        data = pd.Series(data, index=ensys.total_time_steps)

    # If data is already a pandas Series but the index does not match the time
    # index of the energy system model --> replace the index
    elif isinstance(data, pd.Series) and list(sorted(
            data.index)) != ensys.total_time_steps:
        data = pd.Series(data.values, index=ensys.total_time_steps)

    return data


def disassemble_user_expression(expr):
    """ Disassemble a user-specified expression in its pieces. """
    expr = expr.replace(' ', '')  # remove all spaces
    # List of reserved chars that are used for string splitting:
    reserved_chars_1 = ['*', '/', '+', '-', '(', ')']
    reserved_chars_2 = ['==', '>=', '<=', '**']
    # Do the string splitting. Exemplary output:
    # ['Q', '==', 'xx', '*', '(', 'F', '/', '0.3', ')', '**', '3']
    expr_part = []
    while len(expr) > 0:
        store_string = ''
        for i in range(len(expr)):
            if expr[i:i + 2] in reserved_chars_2:  # two signs in a row
                if store_string:  # is not empty
                    expr_part.append(store_string)
                expr_part.append(expr[i:i + 2])  # reserved chars
                expr = expr[len(store_string) + 2:len(expr)]
                break
            elif expr[i] in reserved_chars_1:  # one sign
                if store_string:  # is not empty
                    expr_part.append(store_string)
                expr_part.append(expr[i:i + 1])
                expr = expr[len(store_string) + 1:len(expr)]
                break
            else:
                store_string += expr[i]
                # If string is in last position of expression
                if len(expr) == len(store_string):
                    expr_part.append(store_string)
                    expr = expr[len(store_string):len(expr)]  # -> expr = ''
    return expr_part

# ==============================================================================
#    S I M P L I F Y   U S E R   C O N S T R A I N T
# ==============================================================================
def simplify_user_constraint(df):
    """
    Simplify a user-defined constraint in multiple iterations until the provided
    DataFrame holds only 3 columns (left hand side, le/eq/ge, right hand side).
    ==> The data from the simplified DataFrame is returned as python dicts for
        "lhs" and "rhs" and a string for the operation sign ('==', '>=', '<=').

    Exemplary string representation of the original user_expression:
    '-Q == (1 + F * 0.8) ** 3'

    Stepwise simplification process of the original DataFrame:
         0            1   2  3    4  5            6  7    8  9   10   11
    0 0  -  comp.Q[0,0]  ==  (  1.0  +  comp.F[0,0]  *  0.8  )  **  3.0
      1  -  comp.Q[0,1]  ==  (  1.0  +  comp.F[0,1]  *  0.8  )  **  3.0
      2  -  comp.Q[0,2]  ==  (  1.0  +  comp.F[0,2]  *  0.8  )  **  3.0
      [...]
         0            1   2  3    4  5                6  7   8    9
    0 0  -  comp.Q[0,0]  ==  (  1.0  +  0.8*comp.F[0,0]  )  **  3.0
      1  -  comp.Q[0,1]  ==  (  1.0  +  0.8*comp.F[0,1]  )  **  3.0
      2  -  comp.Q[0,2]  ==  (  1.0  +  0.8*comp.F[0,2]  )  **  3.0
      [...]
         0            1   2  3                      4  5   6    7
    0 0  -  comp.Q[0,0]  ==  (  1.0 + 0.8*comp.F[0,0]  )  **  3.0
      1  -  comp.Q[0,1]  ==  (  1.0 + 0.8*comp.F[0,1]  )  **  3.0
      2  -  comp.Q[0,2]  ==  (  1.0 + 0.8*comp.F[0,2]  )  **  3.0
      [...]
         0            1   2                      3   4    5
    0 0  -  comp.Q[0,0]  ==  1.0 + 0.8*comp.F[0,0]  **  3.0
      1  -  comp.Q[0,1]  ==  1.0 + 0.8*comp.F[0,1]  **  3.0
      2  -  comp.Q[0,2]  ==  1.0 + 0.8*comp.F[0,2]  **  3.0
      [...]
         0            1   2                             3
    0 0  -  comp.Q[0,0]  ==  (1.0 + 0.8*comp.F[0,0])**3.0
      1  -  comp.Q[0,1]  ==  (1.0 + 0.8*comp.F[0,1])**3.0
      2  -  comp.Q[0,2]  ==  (1.0 + 0.8*comp.F[0,2])**3.0
      [...]
                     0   1                             2
    0 0  - comp.Q[0,0]  ==  (1.0 + 0.8*comp.F[0,0])**3.0
      1  - comp.Q[0,1]  ==  (1.0 + 0.8*comp.F[0,1])**3.0
      2  - comp.Q[0,2]  ==  (1.0 + 0.8*comp.F[0,2])**3.0
      [...]
    """
    # Simplify the DataFrame until it has only 3 columns (LHS <==> RHS)
    while_iter_count = 0  # init counter
    while len(df.columns) > 3 and while_iter_count < 100:
        # Increase counter by 1 for each iteration in the while-loop
        while_iter_count += 1
        # Flag to check if mathematical operation has been performed
        # -> if True, jump to beginning of the while-loop (continue)
        operation_done = False  # init
        found_minus_sign = False  # init
        df.columns = range(len(df.columns))  # rename the columns
        first_row = df.iloc[0]  # list of first row entries
        # print(df.head(3).to_string())
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 1. Look for a part of the expression in brackets
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Loop first_row from left, look for first ')' and remember last '('
        last_opening_idx = 0  # init
        first_closing_idx = len(first_row)  # init
        for idx, obj in first_row.items():
            if isinstance(obj, str) and obj == '(':
                last_opening_idx = idx
            if isinstance(obj, str) and obj == ')':
                first_closing_idx = idx
                break
        # Get slice of 'first_row' (in brackets) or whole row if no brackets
        first_row_slice = first_row[last_opening_idx:first_closing_idx + 1]
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 2. Look for exponents in the slice
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Look for power symbol ('**') in expression part
        for idx, obj in first_row_slice.items():
            if isinstance(obj, str) and obj == '**':
                # Find names of surrounding elements of '**' operator
                lhs_idx = idx - 1
                rhs_idx = idx + 1
                rhs_obj = first_row_slice[rhs_idx]
                # If rhs is a minus sign, next element is considered
                if isinstance(rhs_obj, str) and rhs_obj == '-':
                    rhs_idx = idx + 2
                    found_minus_sign = True
                # Do the power operation, depending on the flag
                # 'found_minus_sign' and delete surrounding columns
                if found_minus_sign:
                    df[idx] = df[lhs_idx] ** (-1 * df[rhs_idx])
                    df.drop([idx+2, idx+1, idx-1], axis=1, inplace=True)
                else:
                    df[idx] = df[lhs_idx] ** df[rhs_idx]
                    df.drop([idx + 1, idx - 1], axis=1, inplace=True)
                # Set flag 'operation_done' to True to continue while
                operation_done = True
                break  # the for-loop
        # Jump to the beginning of while-loop if flag is True
        if operation_done:
            continue
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 3. Look for division and multiplication
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Look for division or multiplication symbols in expression part
        for idx, obj in first_row_slice.items():
            if isinstance(obj, str) and (obj == '/' or obj == '*'):
                # Find names of surrounding elements of '/' or '*' operator
                lhs_idx = idx - 1
                rhs_idx = idx + 1
                rhs_obj = first_row_slice[rhs_idx]
                # If rhs is a minus sign, next element is considered
                if isinstance(rhs_obj, str) and rhs_obj == '-':
                    rhs_idx = idx + 2
                    found_minus_sign = True
                # Do the operation, depending on the flag 'found_minus_sign'
                # and the found operator and delete surrounding columns
                if found_minus_sign:
                    if obj == '/':
                        df[idx] = df[lhs_idx] / (-1 * df[rhs_idx])
                    else:  # obj == '*'
                        df[idx] = df[lhs_idx] * (-1 * df[rhs_idx])
                    df.drop([idx+2, idx+1, idx-1], axis=1, inplace=True)
                else:
                    if obj == '/':
                        df[idx] = df[lhs_idx] / df[rhs_idx]
                    else:  # obj == '*'
                        df[idx] = df[lhs_idx] * df[rhs_idx]
                    df.drop([idx + 1, idx - 1], axis=1, inplace=True)
                # Set flag 'operation_done' to True to continue while
                operation_done = True
                break  # the for-loop
        # Jump to the beginning of while-loop if flag is True
        if operation_done:
            continue
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 4. Look for summation and subtraction
        #    (--> Combinations: -+ or ++ are not allowed!)
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Look for summation and subtraction symbols in expression part
        for idx, obj in first_row_slice.items():
            if isinstance(obj, str) and (obj == '+' or obj == '-'):
                # ------------------------------------------------------
                # Special case I: Plus or minus operator in first position
                if idx == 0:
                    if obj == '-':
                        df[1] = -1 * df[1]
                    # else --> obj == '+' --> pass
                    df.drop([0], axis=1, inplace=True)  # delete first col
                    operation_done = True
                    break  # the for-loop
                # ------------------------------------------------------
                # Find names of surrounding elements of '+' or '-' operator
                lhs_idx = idx - 1
                lhs_obj = first_row_slice[lhs_idx]
                rhs_idx = idx + 1
                rhs_obj = first_row_slice[rhs_idx]
                # ------------------------------------------------------
                # Special case II: Plus or minus operator is right beside an
                # opening bracket or an (non)-equality sign.
                if isinstance(lhs_obj, str) and (
                        lhs_obj == '(' or lhs_obj == '==' or
                        lhs_obj == '>=' or lhs_obj == '<='):
                    if obj == '-':
                        df[rhs_idx] = -1 * df[rhs_idx]
                    # else --> obj == '+' --> pass
                    df.drop([idx], axis=1, inplace=True)
                    operation_done = True
                    break  # the for-loop
                # ------------------------------------------------------
                # If rhs is a minus sign, next element is considered
                if isinstance(rhs_obj, str) and rhs_obj == '-':
                    rhs_idx = idx + 2
                    found_minus_sign = True
                # Do the operation, depending on the flag 'found_minus_sign'
                # and the found operator and delete surrounding columns
                if found_minus_sign:
                    if obj == '+':
                        df[idx] = df[lhs_idx] + (-1 * df[rhs_idx])
                    else:  # obj == '-'
                        df[idx] = df[lhs_idx] - (-1 * df[rhs_idx])
                    df.drop([idx+2, idx+1, idx-1], axis=1, inplace=True)
                else:
                    if obj == '+':
                        df[idx] = df[lhs_idx] + df[rhs_idx]
                    else:  # obj == '-'
                        df[idx] = df[lhs_idx] - df[rhs_idx]
                    df.drop([idx + 1, idx - 1], axis=1, inplace=True)
                # Set flag 'operation_done' to True to continue while
                operation_done = True
                break  # the for-loop
        # Jump to the beginning of while-loop if flag is True
        if operation_done:
            continue
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # 5. Delete enclosing brackets
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # This point it reached, if an expression slice does not contain
        # any more possibilities to perform the mathematical operations
        # 'pow', 'div', 'mul', 'add', 'sub'. Check if the term is still
        # enclosed by brackets --> remove them.
        idx = first_row_slice.keys()
        if first_row_slice[idx[0]] == '(' and first_row_slice[idx[-1]] == ')':
            df.drop([idx[0], idx[-1]], axis=1, inplace=True)
            # Set flag 'operation_done' to True to continue while
            operation_done = True
        # Jump to the beginning of while-loop if flag is True
        if operation_done:
            continue

    # Outside of while-loop:
    # ~~~~~~~~~~~~~~~~~~~~~~
    # Raise an error if too many iterations are performed on one constraint!
    if while_iter_count >= 100:
        raise ValueError('The function "simplify_user_constraint" needed too '
                         'many iterations. The simplification process stopped '
                         'before the constraint could be simplified to the '
                         'desired form "LHS <==> RHS". Check your constraints!')

    # Final renaming of last three columns to [1, 2, 3]
    df.columns = range(len(df.columns))
    # print(df.head(3).to_string())
    # print('Number of while-loops:', str(while_iter_count))

    # Convert the first and the third column to python dictionaries and get the
    # global operation sign from the first row of the middle column.
    lhs = df[0].to_dict()
    op = df[1].iloc[0]  # done only once --> it's the same operator in all rows
    rhs = df[2].to_dict()

    # Return the left and right hand side dicts and the operator sign
    return lhs, op, rhs
# ==============================================================================

def check_add_icc(which, inc_exist, inc_mod):
    if which != 'all' and not isinstance(which, list):
        raise TypeError(
            'The "which_instances" keyword can either take string '
            '"all" or can hold a list of component names!')
    is_boolean(inc_exist), is_boolean(inc_mod)


def check_clustering_input(number_of_typical_periods,
                           number_of_time_steps_per_period,
                           total_number_of_time_steps):
    is_strictly_positive_int(number_of_typical_periods)
    is_strictly_positive_int(number_of_time_steps_per_period)
    if not total_number_of_time_steps % number_of_time_steps_per_period == 0:  # TODO: There should be a possibility to use other period lengths as well
        raise ValueError('The number_of_time_steps_per_period has to be an '
                         'integer divisor of the total number of time steps '
                         'considered in the energy system model.')
    if total_number_of_time_steps < \
            number_of_typical_periods * number_of_time_steps_per_period:
        raise ValueError('The product of the number_of_typical_periods and the '
                         ' number_of_time_steps_per_period has to be smaller'
                         ' than the total number of considered time steps.')


def check_declare_optimization_problem_input(time_series_aggregation,
                                             is_data_clustered,
                                             persistent_model,
                                             persistent_solver):
    if not isinstance(time_series_aggregation, bool):
        raise TypeError('Parameter time_series_aggregation has to be boolean.')
    if time_series_aggregation and not is_data_clustered:
        raise ValueError('The time series_aggregation flag indicates possible '
                         'inconsistencies in the aggregated time series data.\n'
                         'First call cluster function and optimize afterwards.')
    if not isinstance(persistent_model, bool):
        raise ValueError('The "persistent_model" parameter has to be boolean!')
    if persistent_solver != 'gurobi_persistent' and \
            persistent_solver != 'cplex_persistent':
        raise ValueError('Valid solvers for the persistent interface are '
                         '"gurobi_persistent" and "cplex_persistent"!')


def check_optimize_input(time_series_aggregation, persistent_model,
                         persistent_solver, is_data_clustered,
                         solver, time_limit, optimization_specs, warmstart):
    """ Check correctness of input arguments to the optimize function of the
     energy system model instance"""
    check_declare_optimization_problem_input(time_series_aggregation,
                                             is_data_clustered,
                                             persistent_model,
                                             persistent_solver)
    if not isinstance(solver, str):
        raise TypeError('The solver parameter has to be a string.')
    if time_limit is not None:
        is_strictly_positive_int(time_limit)
    if not isinstance(optimization_specs, str):
        raise TypeError('The optimization_specs parameter has to be a string.')
    if not isinstance(warmstart, bool):
        raise ValueError('The warmstart parameter has to be a boolean.')


def input_check_energy_system_model(number_of_time_steps, hours_per_time_step,
                                    interest_rate, economic_lifetime, logging):
    """ Check the correctness of the user input for the initialization of an
    EnergySystemModel instance. """
    is_strictly_positive_int(number_of_time_steps)
    is_strictly_positive_int(hours_per_time_step)
    is_strictly_positive_int(economic_lifetime)
    is_positive_number(interest_rate)

    if logging is not None and not isinstance(logging, aristopy.Logger):
        raise TypeError('"logging" only takes instances of the class "Logger"')


def check_design_parameters(has_cap, has_is_built, is_built_fix,
                            cap_min, cap_max):
    """ Check input arguments of design parameters and their combinations. """
    for val, var in zip([has_cap, has_is_built, is_built_fix],
                        ['has_capacity_variable',
                         'has_is_built_binary_variable', 'is_built_fix']):
        if not isinstance(val, bool):
            raise ValueError('The domain of the variable {} has to be boolean.'
                             .format(var))
    if not has_cap and has_is_built:
        raise ValueError('Capacity variables are required, when '
                         'has_is_built_binary_variable is set to True.')
    if cap_min is not None:
        is_positive_number(cap_min)
    if cap_max is not None:
        is_positive_number(cap_max)


def check_edit_var_input(variable, store_vars, **kwargs):
    is_string(variable)
    is_boolean(store_vars)
    for key, val in kwargs.items():
        if key not in ['ub', 'lb', 'domain', 'has_time_set', 'init']:
            warnings.warn('Keyword argument "{}" not recognized. Options '
                          'for variable editing are: "domain", "ub", "lb", '
                          '"has_time_set", "init".'.format(key))

        if key == 'ub' or key == 'lb':
            if val is not None:
                is_number(val)
        if key == 'domain':
            if val not in ['Binary', 'NonNegativeReals', 'Reals']:
                raise TypeError('Select the domain of the variable from '
                                '"Binary", "NonNegativeReals", "Reals"')
        if key == 'has_time_set':
            is_boolean(val)


# TODO: Used somewhere? Delete it if not!
def check_fix_existence_input(which, val, inc_mods, fix_cap):
    if which != 'all' and which != 'current' and not isinstance(which, list):
        raise TypeError('The "which_instance" keyword can either take strings '
                        '"all" or "current" or can hold a list of integers!')
    if val != 1 and val != 0 and val != 'current':
        raise TypeError('The "value" keyword can either hold the integers 1 or '
                        '0 or the string "current"!')
    is_boolean(inc_mods), is_boolean(fix_cap)


def check_relax_integrality(which, inc_exist, inc_mod, inc_time, store_vars):
    if which != 'all' and not isinstance(which, list):
        raise TypeError('The "which_instances" keyword can either take string '
                        '"all" or can hold a list of component names!')
    is_boolean(inc_exist), is_boolean(inc_mod), is_boolean(inc_time), \
        is_boolean(store_vars)


def is_boolean(value):
    if not isinstance(value, bool):
        raise TypeError('The input argument has to be boolean (True or False).')


def is_energy_system_model_instance(ensys):
    if not isinstance(ensys, aristopy.EnergySystemModel):
        raise TypeError('The input is not an EnergySystemModel instance.')


def is_number(value):
    if not (isinstance(value, float) or isinstance(value, int)):
        raise TypeError('The input argument has to be a number.')


def is_positive_number(value):
    """ Check if the input argument is a positive number. """
    is_number(value)
    if not value >= 0:
        raise ValueError('The input argument has to be positive.')


def is_pyomo_object(obj):
    if not (isinstance(obj, pyomo.Set) or isinstance(obj, pyomo.Param) or
            isinstance(obj, pyomo.Var) or isinstance(obj, pyomo.Constraint)):
        raise TypeError('The input is not an valid pyomo object. Valid objects '
                        'are: sets, parameters, variables and constraints.')


def is_strictly_positive_int(value):
    """ Check if the input argument is a strictly positive integer. """
    if not type(value) == int:
        raise TypeError('The input argument has to be an integer.')
    if not value > 0:
        raise ValueError('The input argument has to be strictly positive.')


def is_string(string):
    """ Check if the input argument is a string. """
    if not type(string) == str:
        raise TypeError('The input argument has to be a string')


# Todo: delete this
# def output(message, verbose, val):
#     if verbose == val:
#         print(message)
