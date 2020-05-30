#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
** The Storage class **

* Last edited: 2020-01-01
* Created by: Stefan Bruche (TU Berlin)
"""
import pyomo.environ as pyomo

from aristopy import utils
from aristopy.component import Component


class Storage(Component):
    # Storage components store commodities and transfer them between time steps.
    def __init__(self, ensys, name, basic_variable='inlet_variable',
                 inlet=None, outlet=None,
                 has_existence_binary_var=False,
                 time_series_data=None, scalar_params=None,
                 additional_vars=None, user_expressions=None,
                 capacity=None, capacity_min=None, capacity_max=None,
                 capacity_per_module=None, maximal_module_number=None,
                 capex_per_capacity=0, capex_if_exist=0,
                 opex_per_capacity=0, opex_if_exist=0, opex_operation=0,
                 charge_rate=1, discharge_rate=1, self_discharge=0,
                 charge_efficiency=1, discharge_efficiency=1,
                 soc_min=0, soc_max=1, soc_initial=None,
                 use_inter_period_formulation=True,
                 precise_inter_period_modeling=False
                 ):
        """
        Initialize a storage component.

        :param ensys:
        :param name:
        :param basic_variable:
        :param inlet:
        :param outlet:
        :param has_existence_binary_var:
        :param time_series_data:
        :param scalar_params:
        :param additional_vars:
        :param user_expressions:
        :param capacity:
        :param capacity_min:
        :param capacity_max:
        :param capacity_per_module:
        :param maximal_module_number:
        :param capex_per_capacity:
        :param capex_if_exist:
        :param opex_per_capacity:
        :param opex_if_exist:
        :param opex_operation:
        :param charge_rate:
        :param discharge_rate:
        :param self_discharge:
        :param soc_min:
        :param soc_max:
        """

        # Set an upper bound for the storage capacity if nothing is specified to
        # make sure that storage components always have a capacity variable!
        if not capacity and not capacity_min and not capacity_max:
            capacity_max = 1e6

        Component.__init__(self, ensys, name, basic_variable=basic_variable,
                           inlet=inlet, outlet=outlet,
                           has_existence_binary_var=has_existence_binary_var,
                           time_series_data=time_series_data,
                           scalar_params=scalar_params,
                           additional_vars=additional_vars,
                           user_expressions=user_expressions,
                           capacity=capacity,
                           capacity_min=capacity_min,
                           capacity_max=capacity_max,
                           capacity_per_module=capacity_per_module,
                           maximal_module_number=maximal_module_number,
                           capex_per_capacity=capex_per_capacity,
                           capex_if_exist=capex_if_exist,
                           opex_per_capacity=opex_per_capacity,
                           opex_if_exist=opex_if_exist,
                           opex_operation=opex_operation
                           )

        # Check and set storage specific input arguments
        self.charge_rate = utils.set_if_positive(charge_rate)
        self.discharge_rate = utils.set_if_positive(discharge_rate)
        self.self_discharge = utils.set_if_between_zero_and_one(self_discharge)
        self.charge_efficiency = utils.set_if_between_zero_and_one(
            charge_efficiency)
        self.discharge_efficiency = utils.set_if_between_zero_and_one(
            discharge_efficiency)
        self.soc_min = utils.set_if_between_zero_and_one(soc_min)
        self.soc_max = utils.set_if_between_zero_and_one(soc_max)
        self.soc_initial = utils.set_if_between_zero_and_one(soc_initial) \
            if soc_initial is not None else None

        utils.is_boolean(use_inter_period_formulation)  # check input
        self.use_inter_period_formulation = use_inter_period_formulation
        utils.is_boolean(precise_inter_period_modeling)
        self.precise_inter_period_modeling = precise_inter_period_modeling

        # Store the names of the charging and discharging variables
        if len(self.inlet) == 0 or len(self.outlet) == 0:
            raise Exception('Storage needs at least one inlet and outlet Flow!')
        self.charge_variable = self.inlet[0].var_name
        self.discharge_variable = self.outlet[0].var_name

        # Create a state of charge (SOC) variable and if the inter-period
        # formulation is selected create an additional inter-period SOC variable
        if not self.use_inter_period_formulation:
            self._add_var(utils.SOC, has_time_set=False,
                          alternative_set='intra_period_time_set')  # NonNegReal
        # use inter-period formulation:
        else:
            self._add_var(utils.SOC, domain='Reals', has_time_set=False,
                          alternative_set='intra_period_time_set')  # Real
            self._add_var(utils.SOC_INTER, has_time_set=False,
                          alternative_set='inter_period_time_set')
            if not self.precise_inter_period_modeling:
                self._add_var(utils.SOC_MAX, has_time_set=False,
                              alternative_set='typical_periods_set',
                              domain='Reals')
                self._add_var(utils.SOC_MIN, has_time_set=False,
                              alternative_set='typical_periods_set',
                              domain='Reals')

        # Last step: Add the component to the energy system model instance
        self.add_to_energy_system_model(ensys, name)

    def __repr__(self):
        return '<Storage: "%s">' % self.name

    def declare_component_constraints(self, ensys, pyM):
        """
        Declare time independent and dependent constraints.

        :param ensys: EnergySystemModel instance representing the energy system
            in which the component should be added.
        :type ensys: EnergySystemModel class instance

        :param pyM: Pyomo ConcreteModel which stores the mathematical
            formulation of the energy system model.
        :type pyM: Pyomo ConcreteModel
        """
        # Time independent constraints:
        # -----------------------------
        self.con_couple_bi_ex_and_cap()
        self.con_cap_min()
        self.con_cap_modular()
        self.con_modular_sym_break()
        self.con_couple_existence_and_modular()

        # Time dependent constraints:
        # ---------------------------
        self.con_operation_limit(pyM)
        self.con_soc_balance(ensys, pyM)
        self.con_charge_rate(ensys, pyM)
        self.con_discharge_rate(ensys, pyM)
        self.con_cyclic_condition(ensys, pyM)
        self.con_soc_initial(ensys, pyM)
        self.con_soc_intra_period_start(ensys, pyM)  # only if inter-period f.
        self.con_soc_inter_period_balance(ensys, pyM)  # only if inter-period f.
        self.con_soc_bounds_without_inter_period_formulation(ensys, pyM)
        self.con_soc_bounds_with_inter_period_formulation_simple(ensys, pyM)
        self.con_soc_bounds_with_inter_period_formulation_precise(ensys, pyM)

    def get_objective_function_contribution(self, ensys, pyM):
        """ Get contribution to the objective function. """
        # Check if the component is completely unconnected. If this is True,
        # don't use the objective function contributions of this component
        # (could create infeasibilities!)
        if len(self.var_connections.keys()) == 0:
            self.log.warn('Found an unconnected component! Skipped possible '
                          'objective function contributions.')
            return 0

        # Call function in "Component" class and calculate CAPEX and OPEX
        super().get_objective_function_contribution(ensys, pyM)

        return sum(self.comp_obj_dict.values())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #    A D D I T I O N A L   T I M E   D E P E N D E N T   C O N S .
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def con_operation_limit(self, pyM):
        """
        The operation of a storage component (state of charge) is limit by its
        nominal capacity E.g.: |br|
        ``SOC[p, t] <= CAP``
        """
        # Get variables:
        cap = self.variables[utils.CAP]['pyomo']
        soc = self.variables[utils.SOC]['pyomo']

        def con_operation_limit(m, p, t):
            return soc[p, t] <= cap

        setattr(self.pyB, 'con_operation_limit', pyomo.Constraint(
            pyM.time_set, rule=con_operation_limit))

    def con_soc_balance(self, ensys, pyM):
        """
        Constraint that connects the state of charge (SOC) with the charge and
        discharge operation: the change in the state of charge between two
        points in time has to match the values of charging and discharging
        and the self-discharge of the storage (explicit Euler formulation).
        Note that the SOC is not necessarily a value between 0 and 1 here.
        """
        # Get variables:
        charge = self.variables[self.charge_variable]['pyomo']
        discharge = self.variables[self.discharge_variable]['pyomo']
        soc = self.variables[utils.SOC]['pyomo']
        dt = ensys.hours_per_time_step

        def con_soc_balance(m, p, t):
            return soc[p, t+1] == soc[p, t] * (1-self.self_discharge)**dt \
                   + charge[p, t] * self.charge_efficiency \
                   - discharge[p, t] / self.discharge_efficiency

        setattr(self.pyB, 'con_soc_balance', pyomo.Constraint(
            pyM.time_set, rule=con_soc_balance))

    def con_charge_rate(self, ensys, pyM):
        """
        XXX
        """
        cap = self.variables[utils.CAP]['pyomo']
        charge = self.variables[self.charge_variable]['pyomo']
        dt = ensys.hours_per_time_step

        def con_charge_rate(m, p, t):
            return charge[p, t] <= cap * dt * self.charge_rate

        setattr(self.pyB, 'con_charge_rate', pyomo.Constraint(
            pyM.time_set, rule=con_charge_rate))

    def con_discharge_rate(self, ensys, pyM):
        """
        XXX
        """
        cap = self.variables[utils.CAP]['pyomo']
        discharge = self.variables[self.discharge_variable]['pyomo']
        dt = ensys.hours_per_time_step

        def con_discharge_rate(m, p, t):
            return discharge[p, t] <= cap * dt * self.discharge_rate

        setattr(self.pyB, 'con_discharge_rate', pyomo.Constraint(
            pyM.time_set, rule=con_discharge_rate))

    def con_cyclic_condition(self, ensys, pyM):
        """
        State of charge storage in last time step (after last charging and
        discharging events) equals SOC in first time step.
        TODO: Extend explanation!
        """
        # Get variables:
        soc = self.variables[utils.SOC]['pyomo']

        if self.use_inter_period_formulation and ensys.is_data_clustered:
            soc_inter = self.variables[utils.SOC_INTER]['pyomo']

            def con_cyclic_condition_inter(m):
                last_idx = pyM.inter_period_time_set.last()
                return soc_inter[0] == soc_inter[last_idx]

            setattr(self.pyB, 'con_cyclic_condition_inter', pyomo.Constraint(
                rule=con_cyclic_condition_inter))

        else:
            # Use the formulation without inter-period time steps. This version
            # is computationally less challenging. All periods represent
            # independent entities. Energy cannot be transferred between periods
            # Only one "typical period" exists if data is not clustered [0]
            def con_cyclic_condition(m, p):
                last_t_idx = pyM.intra_period_time_set.last()[1]
                return soc[p, 0] == soc[p, last_t_idx]

            setattr(self.pyB, 'con_cyclic_condition', pyomo.Constraint(
                pyM.typical_periods_set, rule=con_cyclic_condition))

    def con_soc_initial(self, ensys, pyM):
        """
        A value for the relative state of charge in the first time step of each
        period can be specified here. (same value for all periods)
        """
        if self.soc_initial is not None:
            # Get variables:
            soc = self.variables[utils.SOC]['pyomo']
            cap = self.variables[utils.CAP]['pyomo']

            if self.use_inter_period_formulation and ensys.is_data_clustered:
                soc_inter = self.variables[utils.SOC_INTER]['pyomo']

                def con_soc_inter_initial(m):
                    return soc_inter[0] == cap * self.soc_initial

                setattr(self.pyB, 'con_soc_inter_initial', pyomo.Constraint(
                    rule=con_soc_inter_initial))

            else:
                # Use the formulation without inter-period time steps. This
                # is computationally less challenging. All periods represent
                # independent entities. Energy can't be transferred between them
                # Only one "typical period" exists if data is not clustered [0]
                def con_soc_initial(m, p):
                    return soc[p, 0] == cap * self.soc_initial

                setattr(self.pyB, 'con_soc_initial', pyomo.Constraint(
                    pyM.typical_periods_set, rule=con_soc_initial))

    def con_soc_intra_period_start(self, ensys, pyM):
        """
        Eq. V
        """
        if self.use_inter_period_formulation and ensys.is_data_clustered:
            # Get variables:
            soc = self.variables[utils.SOC]['pyomo']

            def con_soc_intra_period_start(m, p):
                return soc[p, 0] == 0

            setattr(self.pyB, 'con_soc_intra_period_start', pyomo.Constraint(
                pyM.typical_periods_set, rule=con_soc_intra_period_start))

    def con_soc_inter_period_balance(self, ensys, pyM):
        """
        Calculate next inter-period SOC from the previous one and the SOC in the
        last intra-period time step. Also account for self-discharge losses
        associated with SOC_INTER --> results in steps in the overall SOC line!
        """
        if self.use_inter_period_formulation and ensys.is_data_clustered:
            # Get variables:
            soc = self.variables[utils.SOC]['pyomo']
            soc_inter = self.variables[utils.SOC_INTER]['pyomo']
            dt = ensys.hours_per_time_step

            def con_soc_inter_period_balance(m, p):
                typ_period = ensys.periods_order[p]
                last_ts_idx = pyM.intra_period_time_set.last()[1]
                return soc_inter[p + 1] == soc_inter[p] * (
                        1 - self.self_discharge)**(
                        ensys.number_of_time_steps_per_period * dt) + soc[
                    typ_period, last_ts_idx]

            setattr(self.pyB, 'con_soc_inter_period_balance', pyomo.Constraint(
                ensys.periods, rule=con_soc_inter_period_balance))

    def con_soc_bounds_without_inter_period_formulation(self, ensys, pyM):
        """
        Is applied if the inter period formulation is not selected or the data
        is not clustered!
        """
        if not self.use_inter_period_formulation or not ensys.is_data_clustered:
            # Get variables:
            soc = self.variables[utils.SOC]['pyomo']
            cap = self.variables[utils.CAP]['pyomo']

            # Todo: Causes errors when calculating iteratively because this
            #  formulation changes the bounds permanently to NonNegativeReals.
            #  Hence, you cannot do clustering in a second iteration.
            #  Simply use the min-value to get lb of zero.
            # Todo: Remove this part after proper testing!
            # If the domain of the SOC variable is 'Reals' (this is possible if
            # the storage component is constructed with the attribute
            # "use_inter_period_formulation"=True but the time series
            # aggregation was not performed before optimization.
            # ==> Change the domain of SOC to NonNegativeReals.
            # Workaround: "edit_variable" is only working partially (editing
            # the "variables" and "variables_copy" DataFrames) because the
            # model is not fully declared yet (flag "is_model_declared" is
            # still False). Manually overwrite domain of SOC variable here!
            # if soc[soc.index_set().first()].domain == pyomo.Reals:
            #    self.edit_variable(utils.SOC,
            #                       domain='NonNegativeReals')
            #    soc.domain = pyomo.NonNegativeReals
            # Only built the constraint if the value for soc_min > 0.
            # Otherwise it is already considered by the variable bound (NonNegR)
            # if self.soc_min > 0:
            def con_minimal_soc(m, p, t):
                return soc[p, t] >= cap * self.soc_min

            setattr(self.pyB, 'con_minimal_soc', pyomo.Constraint(
                pyM.intra_period_time_set, rule=con_minimal_soc))

            # Only built the constraint if the value for soc_max is less than 1.
            # Otherwise it is already considered by "con_operation_limit".
            if self.soc_max < 1:
                def con_maximal_soc(m, p, t):
                    return soc[p, t] <= cap * self.soc_max

                setattr(self.pyB, 'con_maximal_soc', pyomo.Constraint(
                    pyM.intra_period_time_set, rule=con_maximal_soc))

    def con_soc_bounds_with_inter_period_formulation_simple(self, ensys, pyM):
        """
        Define the bounds for the state of charge in a simplified way.
        The error is relatively small in comparison the to precise method if
        the specified value for the 'self_discharge' is not too high. However,
        this version requires a reasonable smaller number of constraints but
        also some additional variables.
        """
        if self.use_inter_period_formulation and ensys.is_data_clustered \
                and not self.precise_inter_period_modeling:

            # Get variables:
            soc = self.variables[utils.SOC]['pyomo']
            cap = self.variables[utils.CAP]['pyomo']
            soc_max = self.variables[utils.SOC_MAX]['pyomo']
            soc_min = self.variables[utils.SOC_MIN]['pyomo']
            soc_inter = self.variables[utils.SOC_INTER]['pyomo']
            dt = ensys.hours_per_time_step

            # The variable "SOC_MAX" of a typical period is larger than all
            # occurring intra-period SOCs in the same period (except the last
            # one since it is already used in "SOC_INTER" of the next period)
            def con_soc_max_intra(m, p, t):
                return soc[p, t] <= soc_max[p]

            setattr(self.pyB, 'con_soc_max_intra', pyomo.Constraint(
                pyM.time_set, rule=con_soc_max_intra))

            # The variable "SOC_MIN" of a typical period is smaller than all
            # occurring intra-period SOCs in the same period (except the last
            # one since it is already used in "SOC_INTER" of the next period)
            def con_soc_min_intra(m, p, t):
                return soc[p, t] >= soc_min[p]

            setattr(self.pyB, 'con_soc_min_intra', pyomo.Constraint(
                pyM.time_set, rule=con_soc_min_intra))

            # The inter-period SOC at the beginning of a period plus the maximum
            # intra-period SOC of the associated typical period is less than
            # the available capacity times the maximal usable share (soc_max).
            def con_soc_max_bound_simple(m, p):
                typ_period = ensys.periods_order[p]
                return soc_inter[p] + soc_max[typ_period] <= cap * self.soc_max

            setattr(pyM, 'con_soc_max_bound_simple', pyomo.Constraint(
                ensys.periods, rule=con_soc_max_bound_simple))

            # The inter-period SOC at the beginning of a period minus the
            # maximal self discharge during that period plus the minimum
            # intra-period SOC of the associated typical period is larger than
            # the available capacity times the minimal required SOC (soc_min).
            def con_soc_min_bound_simple(m, p):
                typ_period = ensys.periods_order[p]
                return soc_inter[p] * (1 - self.self_discharge)**(
                        ensys.number_of_time_steps_per_period * dt) + soc_min[
                    typ_period] >= cap * self.soc_min

            setattr(pyM, 'con_soc_min_bound_simple', pyomo.Constraint(
                ensys.periods, rule=con_soc_min_bound_simple))

    def con_soc_bounds_with_inter_period_formulation_precise(self, ensys, pyM):
        """
        Define the bounds for the state of charge in a precise way. This version
        requires two constraints for each time step of the full scale problem.
        """
        if self.use_inter_period_formulation and ensys.is_data_clustered \
                and self.precise_inter_period_modeling:

            # Get variables:
            soc = self.variables[utils.SOC]['pyomo']
            cap = self.variables[utils.CAP]['pyomo']
            soc_inter = self.variables[utils.SOC_INTER]['pyomo']
            dt = ensys.hours_per_time_step

            # The inter-period SOC at the beginning of a period minus the self
            # discharge plus the intra-period SOC in each hour of that period
            # is less than the available capacity times the max. usable share.
            def con_soc_max_bound_precise(m, p, t):
                typ_period = ensys.periods_order[p]
                return soc_inter[p] * (1 - self.self_discharge)**(t * dt) + soc[
                    typ_period, t] <= cap * self.soc_max

            setattr(pyM, 'con_soc_max_bound_precise', pyomo.Constraint(
                ensys.periods, range(ensys.number_of_time_steps_per_period),
                rule=con_soc_max_bound_precise))

            # The inter-period SOC at the beginning of a period minus the self
            # discharge plus the intra-period SOC in each hour of that period
            # is larger than the available capacity times the min. required SOC.
            def con_soc_min_bound_precise(m, p, t):
                typ_period = ensys.periods_order[p]
                return soc_inter[p] * (1 - self.self_discharge)**(t * dt) + soc[
                    typ_period, t] >= cap * self.soc_min

            setattr(pyM, 'con_soc_min_bound_precise', pyomo.Constraint(
                ensys.periods, range(ensys.number_of_time_steps_per_period),
                rule=con_soc_min_bound_precise))

    # ==========================================================================
    #    S E R I A L I Z E
    # ==========================================================================
    def serialize(self):
        comp_dict = super().serialize()
        comp_dict['charge_variable'] = self.charge_variable
        comp_dict['discharge_variable'] = self.discharge_variable
        comp_dict['soc_variable'] = utils.SOC
        comp_dict['soc_inter_variable'] = utils.SOC_INTER
        return comp_dict
