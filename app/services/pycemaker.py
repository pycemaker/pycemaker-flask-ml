# Pandas is used for data manipulation
from threading import Thread
from bson.json_util import dumps
import datetime
from pymongo import MongoClient
import statsmodels.api as sm
import itertools
import warnings
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt
import time

#from pylab import rcParams
#rcParams['figure.figsize'] = 18, 8
# plt.style.use('fivethirtyeight')


warnings.filterwarnings("ignore")


client = MongoClient(
    "mongodb+srv://pycemaker:hlB0VK8dui1pui0p@pycemaker.rbp9n.mongodb.net/pycemaker?retryWrites=true&w=majority")
db = client['pycemaker']
collection = db['observed_features']


class PcmPredict:

    def __init__(self):

        self.y = ""

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

    def get_data_for_train(self, start_date, end_date):

        print("Coletando dados para treino")

        # start = datetime.datetime(2022, 5, 27, 21, 18, 20, 0)
        start = datetime.datetime.strptime(
            start_date, '%Y-%m-%d %H:%M:%S')
        # end = datetime.datetime(2022, 5, 28, 0, 20, 20, 0)
        end = datetime.datetime.strptime(
            end_date, '%Y-%m-%d %H:%M:%S')

        result = collection.find({'date': {'$gte': start, '$lt': end}})
        # result = dumps(result)
        data = pd.DataFrame(result)

        data['cpu_usage'] = [self.cpu_flag(x) for x in data['cpu_usage']]
        data['memory_usage'] = [self.ram_flag(x) for x in data['memory_usage']]
        data['response_time'] = [self.res_flag(
            x) for x in data['response_time']]
        data['request_count'] = data["success_request_count"] + \
            data["fail_request_count"]
        data['request_count'] = [self.req_flag(
            x) for x in data['request_count']]
        data = data.drop(
            columns=["_id", "success_request_count", "fail_request_count"])
        data["health"] = 1 - ((data["cpu_usage"] + data["memory_usage"] +
                              data["response_time"] + data["request_count"]) / 12)

        y = data

        y = y[['date', 'health']]
        # y['date'] = pd.date_range('2022-01-01 00:00:00', freq='5S', periods=len(y)).strftime('%Y-%m-%d %H:%M:%S')
        y['date'] = pd.to_datetime(y['date'])
        y = y.set_index('date')
        y = y.resample('T').mean()
        y['health'] = y['health'].ffill()

        return y

    def get_data_for_test(self, start_date, end_date):

        print("Coletando dados para teste")

        # start = datetime.datetime(2022, 5, 28, 0, 20, 20, 0)
        start = datetime.datetime.strptime(
            start_date, '%Y-%m-%d %H:%M:%S')

        # end = datetime.datetime(2022, 5, 28, 6, 22, 20, 0)
        end = datetime.datetime.strptime(
            end_date, '%Y-%m-%d %H:%M:%S')

        result = collection.find({'date': {'$gte': start, '$lt': end}})

        data3 = pd.DataFrame(result)
        data3['cpu_usage'] = [self.cpu_flag(x) for x in data3['cpu_usage']]
        data3['memory_usage'] = [self.ram_flag(
            x) for x in data3['memory_usage']]
        data3['response_time'] = [self.res_flag(
            x) for x in data3['response_time']]
        data3['request_count'] = data3["success_request_count"] + \
            data3["fail_request_count"]
        data3['request_count'] = [self.req_flag(
            x) for x in data3['request_count']]
        data3 = data3.drop(
            columns=["_id", "success_request_count", "fail_request_count"])
        data3["health"] = 1 - ((data3["cpu_usage"] + data3["memory_usage"] +
                               data3["response_time"] + data3["request_count"]) / 12)

        data3 = data3[['date', 'health']]
        # data3['date'] = pd.date_range('2022-01-01', freq='D', periods=len(data3)).strftime('%Y-%m-%d')
        data3['date'] = pd.to_datetime(data3['date'])
        data3 = data3.set_index('date')
        # data3 = data3.resample('10D').asfreq()
        data3 = data3.resample('T').mean()

        data3['health'] = data3['health'].ffill()

        return data3

    def get_model(self, start_date, end_date):

        print("==========================================================================")

        y = self.get_data_for_train(start_date, end_date)

        start_date = datetime.datetime.strptime(
            start_date, '%Y-%m-%d %H:%M:%S')
        start_date = start_date + datetime.timedelta(minutes=int(2))
        start_date = start_date + datetime.timedelta(hours=int(2))
        start_date = start_date.strftime('%Y-%m-%d %H:%M:%S')

        # teste = self.get_data_for_test(
        #     '2022-05-27 23:20:20', '2022-05-28 00:20:20')

        teste = self.get_data_for_test(start_date, end_date)

        print("Criando modelo")

        mod = sm.tsa.statespace.SARIMAX(y,
                                        order=(1, 0, 1),
                                        seasonal_order=(0, 1, 0, 61),
                                        enforce_stationarity=False,
                                        enforce_invertibility=False)
        results = mod.fit(disp=False)
        # print(results.summary().tables[1])
        self.model = results

        start_date = datetime.datetime.strptime(
            start_date, '%Y-%m-%d %H:%M:%S')
        start_date = start_date.replace(second=0)
        start_date = start_date.strftime('%Y-%m-%d %H:%M:%S')

        end_date = datetime.datetime.strptime(
            end_date, '%Y-%m-%d %H:%M:%S')
        end_date = end_date.replace(second=0)
        end_date = end_date.strftime('%Y-%m-%d %H:%M:%S')

        # pred = self.get_predict_teste(results)
        pred, tempo_restante = self.get_predict(start_date, end_date)

        y_forecasted = pred.predicted_mean
        y_truth = teste.squeeze()
        mse = ((y_forecasted - y_truth) ** 2).mean()

        # print('The Mean Squared Error of our forecasts is {}'.format(round(mse, 2)))
        print('The Mean Squared Error of our forecasts is {}'.format(mse))

        # print('The Root Mean Squared Error of our forecasts is {}'.format(round(np.sqrt(mse), 2)))
        print('The Root Mean Squared Error of our forecasts is {}'.format(np.sqrt(mse)))

        print("==========================================================================")

        return results

    # def get_predict_teste(self, model):

    #     print("Gerando previsão")

    #     pred = model.get_prediction(start=pd.to_datetime(
    #         '2022-05-28 00:20:00'), end=pd.to_datetime('2022-05-28 06:22:00'))

    #     return pred

    def get_predict(self, start_date, end_date):

        print("Gerando previsão")

        pred = self.model.get_prediction(start=pd.to_datetime(
            start_date), end=pd.to_datetime(end_date))

        tempo_restante = self.get_time_to_event(start_date, pred)

        return pred, tempo_restante

    def get_time_to_event_old(self, y, pred):

        print("Calculando tempo até o evento")

        tempo_atual = y.iloc[-1:].index.item()
        tempo_futuro = pred.predicted_mean
        tempo_futuro = tempo_futuro[tempo_futuro <= 0.3]
        tempo_futuro = tempo_futuro.iloc[0:1].index.item()

        tempo_restante = tempo_futuro - tempo_atual

        # print("Faltam %s" % (tempo_restante))
        # print("Faltam %s" % (tempo_futuro))

        return tempo_restante

    def get_time_to_event(self, date_now, pred):

        print("Calculando tempo até o evento")

        try:

            # tempo_atual = y.iloc[-1:].index.item()

            # tempo_atual = datetime.datetime(2022, 5, 28, 0, 20, 00)
            tempo_atual = datetime.datetime.strptime(
                date_now, '%Y-%m-%d %H:%M:%S')
            # print("    %s" % (tempo_atual))

            tempo_futuro = pred.predicted_mean
            tempo_futuro = tempo_futuro[tempo_futuro <= 0.3]
            tempo_futuro = tempo_futuro.iloc[0:1].index.item()

            # print("    %s" % (tempo_futuro))

            tempo_restante = tempo_futuro - tempo_atual

            # print("Faltam %s" % (tempo_restante))
            # print("Faltam %s" % (tempo_futuro))

            print("Time to event: %s" % (tempo_restante))

            return tempo_restante.seconds

        except:

            print("A saúde do sistema estará acima de 30% pelas próximas horas")

            return 0

    def countdown(self, t, tempo_restante):

        print("Iniciando contagem até o evento")

        while t:
            # mins, secs = divmod(t, 60)
            # timer = '{:02d}:{:02d}'.format(mins, secs)
            tempo_restante = tempo_restante - datetime.timedelta(seconds=1)
            print(tempo_restante, end="\r")
            time.sleep(1)
            t -= 1

        print('A estabilidade do sistema está comprometida!')

    def get_current_health(self):
        result = collection.find_one(sort=[('_id', -1)])

        data = result

        print("CPU: %s" % data['cpu_usage'])

        cpu_usage = self.cpu_flag(data['cpu_usage'])
        memory_usage = self.ram_flag(data['memory_usage'])
        response_time = self.res_flag(data['response_time'])
        request_count = data['success_request_count'] + \
            data['fail_request_count']
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


# pcm_predict = PcmPredict()

# # pcm_predict.get_model("2022-05-27 21:18:20", "2022-05-28 00:20:20")
# # pred, tempo_restante = pcm_predict.get_predict(
# #     '2022-05-28 00:20:00', '2022-05-28 06:22:00')
# # print("==========================================================================")

# pcm_predict.get_model("2022-05-30 00:00:00", "2022-05-30 03:00:00")
# pred, tempo_restante = pcm_predict.get_predict(
#     '2022-05-30 03:00:00', '2022-05-30 06:00:00')
# print("==========================================================================")


# # pcm_predict.countdown(tempo_restante.seconds, tempo_restante)

# while True:
#     tempo_atual, tempo_previsao_atual, tempo_restante = pcm_predict.exec_current_health()
#     print("Saúde (Atual): %s, Saúde (Previsão): %s" %
#           (tempo_atual, tempo_previsao_atual))
#     print("==========================================================================")
#     time.sleep(5)
