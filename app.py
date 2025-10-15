#!/usr/bin/env python
# coding: utf-8

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import numpy_financial as npf

# Add external stylesheet (e.g., a Bootswatch theme)
external_stylesheets = [
    "https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css"
]

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)
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

# model 1: too optimistic (all to ETF)
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
    last_monthly_savings = None

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
    last_monthly_savings = monthly_savings
    return buy_net_worth, rent_net_worth, list(range(months)), last_monthly_savings

# model 2: a bit more realistic, 3/4 down payment to savings, 1/4 to ETF
def buying_vs_renting2(purchase_price, down_payment, refurbish, nebenkost_rate, maintenance_rate, property_taxes,
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
    invested_capital_total = down_payment
    invested_capital_ETF = invested_capital_total * 1/4
    invested_capital_savings = invested_capital_total * 3/4
    
    for month in range(months):
        monthly_property_value = purchase_price * ((1 + property_appreciation_rate/12)**month)
        monthly_maintenance = (purchase_price * maintenance_rate)/12
        monthly_taxes = property_taxes / 12
        monthly_buying_cost = monthly_payment + monthly_maintenance + monthly_taxes

        monthly_rent = initial_rent * ((1 + rent_inflation_rate/12) ** month)
        monthly_savings = monthly_buying_cost - monthly_rent

        invested_capital_ETF += monthly_savings
        monthly_investment_return1 = invested_capital_ETF * (investment_return_rate / 12) 
        monthly_investment_return2 = invested_capital_savings * (max((loan_interest_rate - 0.02), 0) / 12) 
        invested_capital_ETF += monthly_investment_return1
        invested_capital_savings += monthly_investment_return2
        invested_capital_total = invested_capital_ETF + invested_capital_savings

        rent_net_worth.append(invested_capital_total)

        outstanding_balance = npf.fv(monthly_loan_interest_rate, month+1, monthly_payment, -loan_amount)
        equity = monthly_property_value - outstanding_balance
        buy_cumulative_cash_flow = equity - inital_payment
        buy_net_worth.append(buy_cumulative_cash_flow)

    return buy_net_worth, rent_net_worth, list(range(months))

# model 3: conserved model
def buying_vs_renting3(purchase_price, down_payment, refurbish, nebenkost_rate, maintenance_rate, property_taxes,
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
    invested_capital_total = down_payment
    invested_capital_ETF = invested_capital_total * 1/8
    invested_capital_savings = invested_capital_total * 7/8
    
    for month in range(months):
        monthly_property_value = purchase_price * ((1 + property_appreciation_rate/12)**month)
        monthly_maintenance = (purchase_price * maintenance_rate)/12
        monthly_taxes = property_taxes / 12
        monthly_buying_cost = monthly_payment + monthly_maintenance + monthly_taxes

        monthly_rent = initial_rent * ((1 + rent_inflation_rate/12) ** month)
        monthly_savings = monthly_buying_cost - monthly_rent

        invested_capital_ETF += monthly_savings
        monthly_investment_return1 = invested_capital_ETF * (investment_return_rate / 12) 
        monthly_investment_return2 = invested_capital_savings * (max(min(loan_interest_rate - 0.02, 0.01), 0) / 12)
        invested_capital_ETF += monthly_investment_return1
        invested_capital_savings += monthly_investment_return2
        invested_capital_total = invested_capital_ETF + invested_capital_savings

        rent_net_worth.append(invested_capital_total)

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
        html.Div([
            html.Label("For reference on interest rates, loan_interest_rat = marginal_lending + 1.5 ~ 3 "),
            html.A("Bundesbank website", href="https://www.bundesbank.de/en", target="_blank"),      
            html.Br(),
            html.Label("For reference on Property Appreciation Rate: "),
            html.A("destatis website", href="https://www.destatis.de/EN/Themes/Economy/Prices/Construction-Prices-And-Real-Property-Prices/_node.html", target="_blank"),
            html.Br(),
            html.Label("For reference on Inflation Rate: "),
            html.A("destatis website", href="https://www.destatis.de/DE/Home/_inhalt.html", target="_blank"),
            html.Br(),
            html.Label("General Inflation Rate is just for reference, it is not taken to the model. Property Appreciation Rate and Rent Inflation Rate is considered beyond Inflation Rate."),
        ]),  
        html.Br(),
        html.Div([
            html.Label("Loan Interest Rate (annual) # this has to be always above 0.02"),
            dcc.Input(id='loan_interest_rate', type='number', value=0.04, step=0.001),
            html.Br(),

            html.Label("Property Appreciation Rate (annual)"),
            dcc.Input(id='property_appreciation_rate', type='number', value=0.01, step=0.001),
            html.Br(),
        ],style={'display': 'inline-block', 'verticalAlign': 'top', 'width': '45%', 'marginRight': '20px'}), 
        
        html.Div([
            html.Label("Rent Inflation Rate (annual)"),
            dcc.Input(id='rent_inflation_rate', type='number', value=0.002, step=0.001),
            html.Br(),

            html.Label("Investment Return Rate (annual) # e.g 4 ~ 10 %"),
            dcc.Input(id='investment_return_rate', type='number', value=0.04, step=0.001),
        ],style={'display': 'inline-block', 'verticalAlign': 'top', 'width': '45%', 'marginRight': '20px'}),
    ],style={'margin': '20px', 'padding': '10px', 'border': '1px solid #ccc'}),

    # Internal parameters block in two columns
    html.Div([
        html.H3("Internal Parameters"),
        html.Div([
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
            html.Label("Initial Rent (monthly)"),
            dcc.Input(id='initial_rent', type='number', value=1000),
            html.Br(),
        ], style={'display': 'inline-block', 'verticalAlign': 'top', 'width': '45%'}),
    ], style={'margin': '20px', 'padding': '10px', 'border': '1px solid #ccc'}),

    html.Hr(),

    # Inputs for Plot 1
    html.Div([
        html.H3("Input for Plot 1 (Loan Term and Monthly Payment)"),
        html.Label("Loan Term: Often 20-30 years, Initial Tilgung(the annual repayment rate): Around 2-3%."),
        html.Br(),
        html.H4("Select Scenario:"),
        dcc.RadioItems(
            id='scenario_selector',
            options=[
                {'label': 'Given Monthly Payment, find Loan Term', 'value': 'monthly_payment_given'},
                {'label': 'Given Loan Term, find Monthly Payment', 'value': 'loan_term_given'}
            ],
            value='loan_term_given'
        ),
        html.Br(),

        # Show/Hide these inputs conditionally
        html.Div([
            html.Label("Monthly Payment (if monthly_payment_given scenario)"),
            dcc.Input(id='input_monthly_payment', type='number', value=1800),
        ], id='monthly_payment_div', style={'display': 'none'}),
        html.Br(),

        html.Div([
            html.Label("Loan Term in Years (if loan_term_given scenario)"),
            dcc.Input(id='input_loan_term', type='number', value=25),
        ], id='loan_term_div', style={'display': 'none'}),
        html.Br(),
        

        html.Button("Update Plot 1", id='update_plot1', n_clicks=0),
        html.Div(id='plot1_results'),
        html.Div(id='plot1_initial_tilgung', style={'marginTop': '10px'}),

        html.Br(),

        # Plot 1 Figure here
        html.H3("Plot 1: Loan Term and Monthly Mortgage Payment"),
        dcc.Graph(id='plot1_figure')
    ], style={'margin': '20px', 'padding': '10px', 'border': '1px solid #ccc'}),

    html.Hr(),

    # Inputs for Plot 2
    html.Div([
        html.H3("Input for Plot 2 ( Buying vs Renting)"),
        html.Label("Loan Term (Years) chosen from Plot 1 result as a conclusion"),
        dcc.Input(id='model_loan_term', type='number', value=25),
        html.Br(),
        html.Button("Update Plot 2", id='update_plot2', n_clicks=0),
        html.Br(),

        html.Div(id='monthly_savings_display', style={'marginBottom': '20px'}),

        # Plot 2 Figure here
        html.H3("Model 1: Buying vs Renting Net Worth Over Time"),
        dcc.Graph(id='plot2_figure'),

        # Add Plot for Model 2
        html.H3("Model 2: Buying vs Renting Net Worth Over Time"),
        dcc.Graph(id='plot2_figure_model2'),
        
        # Add Plot for Model 3
        html.H3("Model 3: Buying vs Renting Net Worth Over Time"),
        dcc.Graph(id='plot2_figure_model3')

    ], style={'margin': '20px', 'padding': '10px', 'border': '1px solid #ccc'})
])

# ---------------------
# Callbacks
# ---------------------
@app.callback(
    [Output('monthly_payment_div', 'style'),
     Output('loan_term_div', 'style')],
     Input('scenario_selector', 'value')
 )
def show_hide_inputs(scenario):
     if scenario == 'monthly_payment_given':
         return {'display': 'block'}, {'display': 'none'}
     else:
         return {'display': 'none'}, {'display': 'block'}
     
@app.callback(
    [Output('plot1_figure', 'figure'),
     Output('plot1_results', 'children'),
     Output('plot1_initial_tilgung', 'children')],
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
   
    tilgung_text = f"Initial Tilgung Rate: {result['initial_tilgung_rate']*100:.2f}% per year of original principal"

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

    return fig, txt, tilgung_text


@app.callback(
    [Output('plot2_figure', 'figure'),
     Output('plot2_figure_model2', 'figure'),
     Output('plot2_figure_model3', 'figure'),
     Output('monthly_savings_display', 'children')],
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
    
    # Compute Model 1
    buy_net_worth_1, rent_net_worth_1, months_list_1,last_monthly_savings_1 = buying_vs_renting(
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
    # Compute Model 2
    buy_net_worth_2, rent_net_worth_2, months_list_2 = buying_vs_renting2(
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

    # Compute Model 3
    buy_net_worth_3, rent_net_worth_3, months_list_3 = buying_vs_renting3(
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

    years_list_1  = [m/12 for m in months_list_1]
    years_list_2  = [m/12 for m in months_list_2]
    years_list_3  = [m/12 for m in months_list_3]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years_list_1, y=buy_net_worth_1, mode='lines', name='Buying'))
    fig.add_trace(go.Scatter(x=years_list_1, y=rent_net_worth_1, mode='lines', name='Renting'))
    fig.update_layout(
        title="too optimistic (all to ETF): Down payment put in e.g ETFs from year 0, having return of Investment Return Rate",
        xaxis_title="Years",
        yaxis_title="Net Worth (€)",
        legend_title="Scenario",
        hovermode="x"
    )

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=years_list_2, y=buy_net_worth_2, mode='lines', name='Buying'))
    fig2.add_trace(go.Scatter(x=years_list_2, y=rent_net_worth_2, mode='lines', name='Renting'))
    fig2.update_layout(
        title="realistic but a bit optimistic: 3/4 Down payment put in e.g bank savings from year 0, having return of (Loan Interest Rate minus 2%), rest 1/4 to ETF from year 0",
        xaxis_title="Years",
        yaxis_title="Net Worth (€)",
        legend_title="Scenario",
        hovermode="x"
    )

    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(x=years_list_3, y=buy_net_worth_3, mode='lines', name='Buying'))
    fig3.add_trace(go.Scatter(x=years_list_3, y=rent_net_worth_3, mode='lines', name='Renting'))
    fig3.update_layout(
        title="very conserved: 7/8 Down payment put in e.g bank savings from year 0, having return of 1% or less, rest 1/8, to ETF from year 0) ",
        xaxis_title="Years",
        yaxis_title="Net Worth (€)",
        legend_title="Scenario",
        hovermode="x"
    )

    monthly_savings_text = f"Last Monthly Savings (Model 1): €{last_monthly_savings_1:.2f}"
    
    return fig,fig2,fig3, monthly_savings_text
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8050,debug=True)
