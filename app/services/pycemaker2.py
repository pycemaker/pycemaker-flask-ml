# Pandas is used for data manipulation
import datetime
from pymongo import MongoClient
import statsmodels.api as sm
import warnings
import pandas as pd
import numpy as np
import time

warnings.filterwarnings("ignore")

class PcmPredict:

    def __init__(self):

        self.y = ""

        self.client = MongoClient(
            "mongodb+srv://pycemaker:hlB0VK8dui1pui0p@pycemaker.rbp9n.mongodb.net/pycemaker?retryWrites=true&w=majority")
        self.db = self.client['pycemaker']

        self.collection_cpu = self.db['cpu_usage']
        self.collection_jvm_memory_usage = self.db['jvm_memory_usage']
        self.collection_request_count = self.db['request_count']
        self.collection_response_time = self.db['response_time']

    def cpu_flag(self, value):
        if value*100 <= 25:
            return 0
        if value*100 <= 50:
            return 1
        if value*100 <= 75:
            return 2
        return 3

    def ram_flag(self, value):
        if value*100 <= 25:
            return 0
        if value*100 <= 50:
            return 1
        if value*100 <= 75:
            return 2
        return 3

    def res_flag(self, value):
        if value <= 0.3:
            return 0
        if value <= 0.6:
            return 1
        if value <= 1:
            return 2
        return 3

    def req_flag(self, value):
        if value <= 15:
            return 0
        if value <= 30:
            return 1
        if value <= 60:
            return 2
        return 3

    def get_data(self, start_date, end_date):
        """
        Function to get data from mongoDB collections

        parameters:
            start_date=
            end_date=

        returns:

        """
        print("Coletando dados para treino")
        start = datetime.datetime.strptime(
            start_date, '%Y-%m-%d %H:%M:%S')
        end = datetime.datetime.strptime(
            end_date, '%Y-%m-%d %H:%M:%S')

        result_cpu = self.collection_cpu.find({'time_series': {'$gte': start, '$lt': end}})
        result_jvm_memory_usage = self.collection_jvm_memory_usage.find({'time_series': {'$gte': start, '$lt': end}})
        result_request_count = self.collection_request_count.find({'time_series': {'$gte': start, '$lt': end}})
        result_response_time = self.collection_response_time.find({'time_series': {'$gte': start, '$lt': end}})

        df_cpu = pd.DataFrame(result_cpu)
        df_jvm_memory_usage = pd.DataFrame(result_jvm_memory_usage)
        df_request_count = pd.DataFrame(result_request_count)
        df_response_time = pd.DataFrame(result_response_time)

        #### Rescale values ​​from 5 seconds to 1 minute average range values
        df_cpu['time_series'] = pd.to_datetime(df_cpu['time_series'])
        df_cpu = df_cpu.set_index('time_series')
        df_cpu = df_cpu.resample('T').mean()

        df_jvm_memory_usage['time_series'] = pd.to_datetime(df_jvm_memory_usage['time_series'])
        df_jvm_memory_usage = df_jvm_memory_usage.set_index('time_series')
        df_jvm_memory_usage = df_jvm_memory_usage.resample('T').mean()

        df_request_count['time_series'] = pd.to_datetime(df_request_count['time_series'])
        df_request_count = df_request_count.set_index('time_series')
        df_request_count = df_request_count.resample('T').mean()

        df_response_time['time_series'] = pd.to_datetime(df_response_time['time_series'])
        df_response_time = df_response_time.set_index('time_series')
        df_response_time = df_response_time.resample('T').mean()

        df_cpu.rename(columns={'value':'cpu_usage'}, inplace=True)
        df_jvm_memory_usage.rename(columns={'value':'memory_usage'}, inplace=True)
        df_response_time.rename(columns={'value':'response_time'}, inplace=True)
        df_request_count.rename(columns={'value_success':'success_request_count'}, inplace=True)
        df_request_count.rename(columns={'value_fail':'fail_request_count'}, inplace=True)

        df_final = df_cpu['cpu_usage'].to_frame()
        df_final = df_final.join(df_jvm_memory_usage['memory_usage'])
        df_final = df_final.join(df_response_time['response_time'])
        df_final = df_final.join(df_request_count['success_request_count'])
        df_final = df_final.join(df_request_count['fail_request_count'])

        df_final['cpu_usage'] = [self.cpu_flag(x) for x in df_final['cpu_usage']]
        df_final['memory_usage'] = [self.ram_flag(x) for x in df_final['memory_usage']]
        df_final['response_time'] = [self.res_flag(x) for x in df_final['response_time']]
        df_final['request_count'] = df_final["success_request_count"] + df_final["fail_request_count"]
        df_final['request_count'] = [self.req_flag(x) for x in df_final['request_count']]

        #### Flag data
        df_final["health"] = 1 - ((df_final["cpu_usage"] + df_final["memory_usage"] + df_final["response_time"] + df_final["request_count"]) / 12)
        y = df_final["health"]

        return y

    def get_model(self, start_date, end_date):

        print("==========================================================================")

        y = self.get_data(start_date, end_date)#getting dataset for training

        start_date = datetime.datetime.strptime(
            start_date, '%Y-%m-%d %H:%M:%S')
        start_date = start_date + datetime.timedelta(minutes=int(2))
        start_date = start_date + datetime.timedelta(hours=int(2))
        start_date = start_date.strftime('%Y-%m-%d %H:%M:%S')

        teste = self.get_data(start_date, end_date) #getting dataset for testing

        print("Criando modelo")

        mod = sm.tsa.statespace.SARIMAX(y,
                                        order=(1, 0, 1),
                                        seasonal_order=(0, 1, 0, 61),
                                        enforce_stationarity=False,
                                        enforce_invertibility=False)
        results = mod.fit(disp=False)

        self.model = results

        start_date = datetime.datetime.strptime(
            start_date, '%Y-%m-%d %H:%M:%S')
        start_date = start_date.replace(second=0)
        start_date = start_date.strftime('%Y-%m-%d %H:%M:%S')

        end_date = datetime.datetime.strptime(
            end_date, '%Y-%m-%d %H:%M:%S')
        end_date = end_date.replace(second=0)
        end_date = end_date.strftime('%Y-%m-%d %H:%M:%S')

        pred = self.get_predict(start_date, end_date)

        y_forecasted = pred.predicted_mean
        y_truth = teste.squeeze()
        mse = ((y_forecasted - y_truth) ** 2).mean()

        print('The Mean Squared Error of our forecasts is {}'.format(mse))

        print('The Root Mean Squared Error of our forecasts is {}'.format(np.sqrt(mse)))

        print("==========================================================================")

        return results

    def get_predict(self, start_date, end_date):

        print("Gerando previsão")

        pred = self.model.get_prediction(start=pd.to_datetime(
            start_date), end=pd.to_datetime(end_date))

        tempo_restante = self.get_time_to_event(start_date, pred)

        return pred, tempo_restante

    def get_time_to_event(self, date_now, pred):

        print("Calculando tempo até o evento")

        try:
            tempo_atual = datetime.datetime.strptime(
                date_now, '%Y-%m-%d %H:%M:%S')

            tempo_futuro = pred.predicted_mean
            tempo_futuro = tempo_futuro[tempo_futuro <= 0.3]
            tempo_futuro = tempo_futuro.iloc[0:1].index.item()
            tempo_restante = tempo_futuro - tempo_atual

            print("Time to event: %s" % (tempo_restante))
            return tempo_restante.seconds

        except:
            print("A saúde do sistema estará acima de 30% pelas próximas horas")
            return 0

    def countdown(self, t, tempo_restante):
        print("Iniciando contagem até o evento")

        while t:
            tempo_restante = tempo_restante - datetime.timedelta(seconds=1)
            print(tempo_restante, end="\r")
            time.sleep(1)
            t -= 1
        print('A estabilidade do sistema está comprometida!')
        return

    def get_current_health(self):
        result_cpu = self.collection_cpu.find_one(sort=[('_id', -1)])
        result_memory = self.collection_jvm_memory_usage.find_one(sort=[('_id', -1)])
        result_rcount = self.collection_request_count.find_one(sort=[('_id', -1)])
        result_rtime = self.collection_response_time.find_one(sort=[('_id', -1)])

        cpu_usage = self.cpu_flag(result_cpu['value'])
        memory_usage = self.ram_flag(result_memory['value'])
        response_time = self.res_flag(result_rtime['value'])
        request_count = result_rcount['value_success'] + \
            result_rcount['value_fail']
        request_count = self.req_flag(request_count)

        current_health = 1 - \
            ((cpu_usage + memory_usage + response_time + request_count) / 12)

        return current_health

    def exec_current_health(self, time_range):

        start_date = datetime.datetime.now()
        start_date = start_date + datetime.timedelta(hours=int(3))
        start_date = start_date + datetime.timedelta(minutes=int(1))
        end_date = start_date + datetime.timedelta(hours=int(time_range))
        start_date = start_date.replace(second=0)
        end_date = end_date.replace(second=0)
        start_date = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date = end_date.strftime('%Y-%m-%d %H:%M:%S')

        pred, tempo_restante = self.get_predict(start_date, end_date)

        tempo_previsao_atual = pred.predicted_mean.iloc[0:1]
        tempo_previsao_atual = tempo_previsao_atual.values[0]
        tempo_atual = self.get_current_health()

        return tempo_atual, tempo_previsao_atual, tempo_restante