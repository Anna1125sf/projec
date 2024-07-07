
import warnings

from dash import Dash, Input, Output, dcc, html
import plotly.express as px
import json
import os
import plotly.graph_objs as go
warnings.filterwarnings("ignore")
import sqlite3

import requests      # Для запросов по API
import time          # Для задержки между запросами
import pandas as pd             # Для удобной загрузки данных в БД
import datetime



def parse_results_fromhh(json_s):
        
    repr= []
    for i in json_s:
        try:
            d_mvf={'id':str(i['id']),
            'name':i['name'],
            'department':i['department'] if i['department']==None else i['department']['name'],
            'response_letter_required':1 if i['response_letter_required'] else 0,
            'type':i['type']['name'],
            'created_at':i['created_at'][:-6],
            'employer': i['employer']['name'],
            'accredited_it_employer': 1 if 'accredited_it_employer' in i['employer'].keys() else 0,
            'schedule':i['schedule']['name'],
            'accept_temporary':1 if i['accept_temporary'] else 0,
            'professional_roles':i['professional_roles'][0]['name'],
            'experience':sum([int(i) for i in i['experience']['name'].split(' ') if i.isnumeric()])/2,
            'employment':i['employment']['name']}
            
            if 'salary' in i.keys():
                d_mvf['salary']=i['salary'] if i['salary']==None else i['salary']['from']
            repr+=[d_mvf]
        except:
            pass
    repr = pd.DataFrame(repr)
    repr[['response_letter_required','accredited_it_employer','accept_temporary']]=repr[['response_letter_required','accredited_it_employer','accept_temporary']].fillna(0).astype(str)
    return repr

def update_data():

        def getPage(page):
            params = {
                'employer_id': 39305,  # ID Газпром
                'page': page,         # Номер страницы
                'per_page': 100       # Кол-во вакансий на 1 странице
            }   
            req = requests.get('https://api.hh.ru/vacancies', params)
            data = req.content.decode() 
            req.close()
            return data
            
        json_s = [] 

        for page in range(0, 100):
            print(page)
            jsObj = json.loads(getPage(page))
            
            json_s+=jsObj['items']

            if (jsObj['pages'] - page) <= 1:  
                break
            time.sleep(0.2)

        repr = parse_results_fromhh(json_s)

        ##### Исключаем дубликаты
        # Устанавливаем соединение с базой данных
                
        dir_current = os.getcwd()
        dir_current = os.path.dirname(os.path.realpath(__file__))
        # Устанавливаем соединение с базой данных
        connection = sqlite3.connect(dir_current+'/my_database.db')
        cursor = connection.cursor()
        cursor.execute('SELECT id FROM resume_data ')
        users = cursor.fetchall()

        users = [i[0] for i in list(users)]
        print(list(users))

        repr= repr.loc[~repr.id.isin(list(users))]

        for i in range(len(repr)):
            data= list(repr.iloc[i])
            cursor.execute('''INSERT INTO resume_data (
            id,name,department,response_letter_required,type,created_at,employer,accredited_it_employer,schedule,accept_temporary,professional_roles,experience,employment,salary

            ) VALUES (?, ?, ?, ?, ?,?, ?, ?, ?, ?,?, ?, ?, ?)''', data)
            connection.commit()
            
        connection.close()
        return html.Div('Data uploaded')

def parse_table(start_date, end_date):
    global df,cursor
    
    # Устанавливаем соединение с базой данных
    
    dir_current = os.getcwd()
    dir_current = os.path.dirname(os.path.realpath(__file__))
    # Устанавливаем соединение с базой данных
    connection = sqlite3.connect(dir_current+'/my_database.db')
    cursor = connection.cursor()

    # Выбираем всех пользователей
    cursor.execute('SELECT * FROM resume_data ')
    users = cursor.fetchall()
    df = pd.DataFrame(list(users),columns = ['id', 'name', 'department', 'response_letter_required', 'type', 'created_at', 'employer', 'accredited_it_employer', 'schedule',
        'accept_temporary', 'professional_roles', 'experience', 'employment',
        'salary'])

    df['date'] = pd.to_datetime(df['created_at'])

    df = df.loc[df["date"].between(pd.to_datetime(start_date),
                    pd.to_datetime(end_date))]
    
    rers=[]

    df["Дата"] = df["date"].map(lambda x: x.date())

    df_sccca = df.groupby('Дата')['type'].count().reset_index()
    df_sccca.columns = ['Дата','Количество']
    scatter = px.scatter(data_frame=df_sccca,
            x='Дата',
            y='Количество')
    
    
    freq = df.response_letter_required.dropna().value_counts().reset_index().rename(columns={"index": "x"}) 
    bar = go.Figure(go.Bar(x=freq.index,y=freq["count"]) )
    bar.update_layout(title = "Сопроводительное письмо")

    freq = df.professional_roles.dropna().value_counts().reset_index().rename(columns={"index": "x"}) 
    pie= go.Figure(go.Pie(labels=freq.professional_roles,  values=freq["count"]) )
    pie.update_layout(title = "Профессиональные роли")

    print(df.professional_roles.unique())

    df_prog = df.loc[df.professional_roles=='Водитель']
    df_dev = df.loc[df.professional_roles=='Лаборант']
    
    hist = go.Figure()
    hist.add_trace(go.Histogram(
        x=df_prog.salary.dropna(),
        histnorm='percent',
        name='Водитель', # name used in legend and hover labels
        nbinsx=20,
        marker_color='#EB89B5',
        opacity=0.75
    ))
    hist.add_trace(go.Histogram(
        x=df_dev.salary.dropna(),
        histnorm='percent',
        name='Лаборант',
        nbinsx=20,

        marker_color='#330C73',
        opacity=0.75
    ))
    hist.update_layout(title = 'Зарплата по видам',
        xaxis_title_text='Value',  yaxis_title_text='Count', # yaxis label
        bargap=0.2, bargroupgap=0.1
    )


    rers += [html.Div([
            html.Div(dcc.Graph(id='map', figure=scatter)),
            html.Div(dcc.Graph(id='map', figure=hist))],
            style={'display': 'flex', 'flexDirection': 'row'}) ]
    rers += [html.Div([
            html.Div(dcc.Graph(id='map', figure=pie)),
            html.Div(dcc.Graph(id='map', figure=bar)) ], 
            style={'display': 'flex', 'flexDirection': 'row'}) ]

    return rers






external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']
app = Dash(__name__, external_stylesheets=external_stylesheets)


app.layout = html.Div([
    html.Button('Получить данные', id='editing-rows-button', n_clicks=0, style={"marginTop": "15px"}),
    html.Div(id='table0'),
    html.Br(),html.Br(),
    html.Div([dcc.DatePickerRange(
            id="date_filter",
            start_date=pd.to_datetime('2024-06-04 23:59:00'),
            end_date=pd.to_datetime('2024-07-04 19:57:01')
        )]),
html.Div(id='table')
])



# CALLBACKS
@app.callback(
    Output("table0", "children"),
    [
        Input("editing-rows-button", "n_clicks"),
    ]
)
def add_row(n_clicks):
    if n_clicks >= 1:
        return update_data()


@app.callback(
    Output("table", "children"),
    Input("date_filter", "start_date"),
    Input("date_filter", "end_date"),
)
def updateGraph(start_date, end_date):
    if not start_date or not end_date:
        raise dash.exceptions.PreventUpdate
    else:
        return parse_table(start_date, end_date)


if __name__ == '__main__':

    import platform

    if platform.system() == 'Windows':
        app.run_server(debug=False)
    else:
        app.run_server(host='0.0.0.0', port=8080)

