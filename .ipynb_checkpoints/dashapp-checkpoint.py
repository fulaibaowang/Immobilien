#!/usr/bin/env python
# coding: utf-8

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import numpy_financial as npf

app = dash.Dash(__name__)
server = app.server

# ---------------------------------
# Functions from your previous code
# ---------------------------------
def calculate_amortization(loan_amount, annual_interest_rate, monthly_payment=None, loan_term=None):
    monthly_interest_rate = annual_interest_rate / 12.0

    if monthly_payment is None and loan_term is not None:
        # Scenario: Known loan_term, find monthly_payment
        total_months = loan_term * 12
        if monthly_interest_rate > 0:
            monthly_payment = (monthly_interest_rate * loan_amount) / (1 - (1 + monthly_interest_rate)**(-total_months))
        else:
            monthly_payment = loan_amount / total_months
    elif monthly_payment is not None and loan_term is None:
        # Scenario: Known monthly_payment, find loan_term
        remaining_balance = loan_amount
        months = 0
        while remaining_balance > 0:
            months += 1
            interest = remaining_balance * monthly_interest_rate
            principal = monthly_payment - interest
            if principal <= 0:
                raise ValueError("Monthly payment too low to cover interest.")
            remaining_balance -= principal
            if months > 1000*12:
                break
        total_months = months
    else:
        raise ValueError("Provide exactly one of (monthly_payment or loan_term).")

    if loan_term is None:
        total_months = months

    # Recalculate total interest
    remaining_balance = loan_amount
    total_interest_paid = 0.0
    for m in range(1, total_months + 1):
        interest = remaining_balance * monthly_interest_rate
        principal = (monthly_payment - interest)
        total_interest_paid += interest
        remaining_balance -= principal
        if remaining_balance < 0:
            remaining_balance = 0

    principal_first_month = monthly_payment - (loan_amount * monthly_interest_rate)
    initial_tilgung_rate = (principal_first_month * 12) / loan_amount

    return {
        "monthly_payment": monthly_payment,
        "total_interest_paid": total_interest_paid,
        "total_months": total_months,
        "initial_tilgung_rate": initial_tilgung_rate
    }

def buying_vs_renting(purchase_price, down_payment, refurbish, nebenkost_rate, maintenance_rate, property_taxes,
                      initial_rent, loan_interest_rate, property_appreciation_rate, rent_inflation_rate,
                      investment_return_rate, loan_term):
    inital_payment = purchase_price * nebenkost_rate + refurbish
    loan_amount = purchase_price - down_payment
    monthly_loan_interest_rate = loan_interest_rate / 12

    years = loan_term
    months = years * 12
    monthly_payment = npf.pmt(monthly_loan_interest_rate, loan_term * 12, -loan_amount)

    buy_net_worth = []
    rent_net_worth = []
    invested_capital = down_payment

    for month in range(months):
        monthly_property_value = purchase_price * ((1 + property_appreciation_rate/12)**month)
        monthly_maintenance = (purchase_price * maintenance_rate)/12
        monthly_taxes = property_taxes / 12
        monthly_buying_cost = monthly_payment + monthly_maintenance + monthly_taxes

        monthly_rent = initial_rent * ((1 + rent_inflation_rate/12) ** month)
        monthly_savings = monthly_buying_cost - monthly_rent

        invested_capital += monthly_savings
        monthly_investment_return = invested_capital * (investment_return_rate / 12)
        invested_capital += monthly_investment_return

        rent_net_worth.append(invested_capital)

        outstanding_balance = npf.fv(monthly_loan_interest_rate, month+1, monthly_payment, -loan_amount)
        equity = monthly_property_value - outstanding_balance
        buy_cumulative_cash_flow = equity - inital_payment
        buy_net_worth.append(buy_cumulative_cash_flow)

    return buy_net_worth, rent_net_worth, list(range(months))

# --------------------------------
# App Layout
# --------------------------------
app.layout = html.Div([
    html.H1("Real Estate Buying vs Renting Model"),

    # External parameters block
    html.Div([
        html.H3("External Parameters"),
        html.Label("Loan Interest Rate (annual) # this has to be always above 0.02"),
        dcc.Input(id='loan_interest_rate', type='number', value=0.04, step=0.001),
        html.Br(),

        html.Label("Property Appreciation Rate (annual)"),
        dcc.Input(id='property_appreciation_rate', type='number', value=0.01, step=0.001),
        html.Br(),

        html.Label("Rent Inflation Rate (annual)"),
        dcc.Input(id='rent_inflation_rate', type='number', value=0.002, step=0.001),
        html.Br(),

        html.Label("Investment Return Rate (annual) # e.g 4 ~ 10 %"),
        dcc.Input(id='investment_return_rate', type='number', value=0.04, step=0.001),
    ], style={'margin': '20px', 'padding': '10px', 'border': '1px solid #ccc', 'width': '400px'}),

    # Internal parameters block in two columns
    html.Div([
        html.H3("Internal Parameters"),

        html.Div([
            html.H4("Buying Parameters"),
            html.Label("Purchase Price # property price"),
            dcc.Input(id='purchase_price', type='number', value=400000),
            html.Br(),

            html.Label("Down Payment"),
            dcc.Input(id='down_payment', type='number', value=100000),
            html.Br(),

            html.Label("Refurbish Cost"),
            dcc.Input(id='refurbish', type='number', value=20000),
            html.Br(),

            html.Label("Nebenkost Rate # Additional cost rate like Notar, Grunderwerbsteuer"),
            dcc.Input(id='nebenkost_rate', type='number', value=0.1, step=0.01),
            html.Br(),

            html.Label("Maintenance Rate (annual) # 1%-2% normal"),
            dcc.Input(id='maintenance_rate', type='number', value=0.015, step=0.001),
            html.Br(),

            html.Label("Property Taxes (annual)"),
            dcc.Input(id='property_taxes', type='number', value=1200),
            html.Br(),
        ], style={'display': 'inline-block', 'verticalAlign': 'top', 'width': '45%', 'marginRight': '20px'}),

        html.Div([
            html.H4("Renting Parameters"),
            html.Label("Initial Rent (monthly)"),
            dcc.Input(id='initial_rent', type='number', value=1000),
            html.Br(),
        ], style={'display': 'inline-block', 'verticalAlign': 'top', 'width': '45%'}),
    ], style={'margin': '20px', 'padding': '10px', 'border': '1px solid #ccc'}),

    html.Hr(),

    # Inputs for Plot 1
    html.Div([
        html.H3("Scenario Input for Plot 1 (Loan Term and Monthly Payment)"),
        html.Label("Select Scenario:"),
        dcc.RadioItems(
            id='scenario_selector',
            options=[
                {'label': 'Given Monthly Payment, find Loan Term', 'value': 'monthly_payment_given'},
                {'label': 'Given Loan Term, find Monthly Payment', 'value': 'loan_term_given'}
            ],
            value='loan_term_given'
        ),
        html.Br(),

        html.Label("Monthly Payment (if monthly_payment_given scenario)"),
        dcc.Input(id='input_monthly_payment', type='number', value=2300),
        html.Br(),

        html.Label("Loan Term in Years (if loan_term_given scenario)"),
        dcc.Input(id='input_loan_term', type='number', value=30),
        html.Br(),

        html.Button("Update Plot 1", id='update_plot1', n_clicks=0),
        html.Div(id='plot1_results'),
        html.Br(),

        # Plot 1 Figure here
        html.H3("Plot 1: Loan Term and Monthly Mortgage Payment"),
        dcc.Graph(id='plot1_figure')
    ], style={'margin': '20px', 'padding': '10px', 'border': '1px solid #ccc'}),

    html.Hr(),

    # Inputs for Plot 2
    html.Div([
        html.H3("Scenario Input for Plot 2 (Model 1: Buying vs Renting)"),
        html.Label("Loan Term (Years) chosen from Plot 1 result as a conclusion"),
        dcc.Input(id='model_loan_term', type='number', value=25),
        html.Br(),
        html.Button("Update Plot 2", id='update_plot2', n_clicks=0),
        html.Br(),

        # Plot 2 Figure here
        html.H3("Plot 2: Buying vs Renting Net Worth Over Time"),
        dcc.Graph(id='plot2_figure')
    ], style={'margin': '20px', 'padding': '10px', 'border': '1px solid #ccc'})
])

# ---------------------
# Callbacks
# ---------------------
@app.callback(
    [Output('plot1_figure', 'figure'),
     Output('plot1_results', 'children')],
    [Input('update_plot1', 'n_clicks')],
    [State('scenario_selector', 'value'),
     State('loan_interest_rate', 'value'),
     State('purchase_price', 'value'),
     State('down_payment', 'value'),
     State('input_monthly_payment', 'value'),
     State('input_loan_term', 'value')]
)
def update_plot1(n_clicks, scenario, loan_interest_rate, purchase_price, down_payment, monthly_payment_given, loan_term_given):
    if n_clicks == 0:
        raise dash.exceptions.PreventUpdate

    loan_amount = purchase_price - down_payment

    # Calculate based on scenario
    if scenario == 'monthly_payment_given':
        # Known monthly payment scenario
        result = calculate_amortization(
            loan_amount=loan_amount,
            annual_interest_rate=loan_interest_rate,
            monthly_payment=monthly_payment_given,
            loan_term=None
        )
        txt = (f"Scenario: Given Monthly Payment\n"
               f"For Monthly Payment={monthly_payment_given}€, Loan Term ≈ {result['total_months']/12:.2f} years. "
               f"Total Interest Paid={result['total_interest_paid']:.2f}€")

    else:
        # Known loan term scenario
        result = calculate_amortization(
            loan_amount=loan_amount,
            annual_interest_rate=loan_interest_rate,
            monthly_payment=None,
            loan_term=loan_term_given
        )
        txt = (f"Scenario: Given Loan Term\n"
               f"For Loan Term={loan_term_given} years, Monthly Payment ≈ {result['monthly_payment']:.2f}€. "
               f"Total Interest Paid={result['total_interest_paid']:.2f}€")

    # The plot always shows the "Monthly Payment vs Loan Term" visualization
    terms = list(range(10, 41))  # from 10 to 40 years
    payments = []
    for t in terms:
        r = calculate_amortization(
            loan_amount=loan_amount,
            annual_interest_rate=loan_interest_rate,
            loan_term=t
        )
        payments.append(r['monthly_payment'])

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=terms, y=payments, mode='lines+markers', name="Monthly Payment"))
    # Highlight if scenario == loan_term_given
    if scenario == 'loan_term_given':
        chosen_payment = result['monthly_payment']
        fig.add_trace(go.Scatter(x=[loan_term_given], y=[chosen_payment],
                                 mode='markers', marker=dict(color='red', size=10),
                                 name='Chosen Term'))
    else:
        # If scenario == monthly_payment_given, we know the resulting loan term from the result
        derived_term = result['total_months']/12
        # Need to find the corresponding payment if we treat this derived term as known
        chosen_payment = np.interp(derived_term, terms, payments)
        fig.add_trace(go.Scatter(x=[derived_term], y=[chosen_payment],
                                 mode='markers', marker=dict(color='green', size=10),
                                 name='Derived Term'))

    fig.update_layout(title="Monthly Payment vs Loan Term",
                      xaxis_title="Loan Term (Years)",
                      yaxis_title="Monthly Payment (€)")

    return fig, txt


@app.callback(
    Output('plot2_figure', 'figure'),
    [Input('update_plot2', 'n_clicks')],
    [State('loan_interest_rate', 'value'),
     State('property_appreciation_rate', 'value'),
     State('rent_inflation_rate', 'value'),
     State('investment_return_rate', 'value'),
     State('purchase_price', 'value'),
     State('down_payment', 'value'),
     State('refurbish', 'value'),
     State('nebenkost_rate', 'value'),
     State('maintenance_rate', 'value'),
     State('property_taxes', 'value'),
     State('initial_rent', 'value'),
     State('model_loan_term', 'value')]
)
def update_plot2(n_clicks, loan_interest_rate, property_appreciation_rate, rent_inflation_rate, investment_return_rate,
                 purchase_price, down_payment, refurbish, nebenkost_rate, maintenance_rate, property_taxes, initial_rent, model_loan_term):
    if n_clicks == 0:
        raise dash.exceptions.PreventUpdate

    buy_net_worth, rent_net_worth, months_list = buying_vs_renting(
        purchase_price=purchase_price,
        down_payment=down_payment,
        refurbish=refurbish,
        nebenkost_rate=nebenkost_rate,
        maintenance_rate=maintenance_rate,
        property_taxes=property_taxes,
        initial_rent=initial_rent,
        loan_interest_rate=loan_interest_rate,
        property_appreciation_rate=property_appreciation_rate,
        rent_inflation_rate=rent_inflation_rate,
        investment_return_rate=investment_return_rate,
        loan_term=model_loan_term
    )

    years_list = [m/12 for m in months_list]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years_list, y=buy_net_worth, mode='lines', name='Buying'))
    fig.add_trace(go.Scatter(x=years_list, y=rent_net_worth, mode='lines', name='Renting'))
    fig.update_layout(
        title="Net Worth Over Time: Buying vs Renting",
        xaxis_title="Years",
        yaxis_title="Net Worth (€)",
        legend_title="Scenario",
        hovermode="x"
    )

    return fig

if __name__ == '__main__':
    app.run_server(debug=True)
