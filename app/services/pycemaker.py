# Pandas is used for data manipulation
import datetime
from pymongo import MongoClient
import statsmodels.api as sm
import warnings
import pandas as pd
import numpy as np
import time
import os
from dotenv import load_dotenv

load_dotenv('.env')

warnings.filterwarnings("ignore")

class PcmPredict:
    """Modelo de Machine Learning para previsão de saúde do servidor a partir de séries temporais do consumo do ambiente
    """
    def __init__(self):
        """Modelo de Machine Learning para previsão de saúde do servidor a partir de séries temporais do consumo do ambiente
        """

        self.client = MongoClient(os.environ.get("MONGO_DB_URL"))
        self.db = self.client['pycemaker']

        self.collection_cpu = self.db['cpu_usage']
        self.collection_jvm_memory_usage = self.db['jvm_memory_usage']
        self.collection_request_count = self.db['request_count']
        self.collection_response_time = self.db['response_time']

    def cpu_flag(self, value):
        """Classifica o dado de consumo da CPU

        Args:
            value (float): Valor do consumo

        Returns:
            int: Flag de consumo
        """
        if value*100 <= 25:
            return 0
        if value*100 <= 50:
            return 1
        if value*100 <= 75:
            return 2
        return 3

    def ram_flag(self, value):
        """Classifica o dado de consumo da Memória

        Args:
            value (float): Valor do consumo

        Returns:
            int: Flag de consumo
        """
        if value*100 <= 25:
            return 0
        if value*100 <= 50:
            return 1
        if value*100 <= 75:
            return 2
        return 3

    def res_flag(self, value):
        """Classifica o dado de tempo de resposta das requisições

        Args:
            value (float): Valor do consumo

        Returns:
            int: Flag de consumo
        """
        if value <= 0.3:
            return 0
        if value <= 0.6:
            return 1
        if value <= 1:
            return 2
        return 3

    def req_flag(self, value):
        """Classifica o dado de número de requisições

        Args:
            value (float): Valor do consumo

        Returns:
            int: Flag de consumo
        """
        if value <= 15:
            return 0
        if value <= 30:
            return 1
        if value <= 60:
            return 2
        return 3

    def get_data(self, start_date, end_date):
        """Busca do banco os dados de consumo do ambiente dentro de um intervalo de tempo;
           Classifica os dados como low(0), medium(1), high(2) e critical(4);
           Obtém a média de cada intervalo de 1 minuto nas séries temporais; e
           Unifica as origens em um unico DataFrame final.

        Args:
            start_date (String): Início do intervalo
            end_date (String): Fim do intervalo

        Returns:
            Pandas DataFrame: DataFrame final com as origens tratadas e unificadas.
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
        df_cpu['cpu_usage'] = [self.cpu_flag(x) for x in df_cpu['value']]
        df_cpu = df_cpu.set_index('time_series')
        df_cpu = df_cpu.resample('T').mean()

        df_jvm_memory_usage['time_series'] = pd.to_datetime(df_jvm_memory_usage['time_series'])
        df_jvm_memory_usage['memory_usage'] = [self.ram_flag(x) for x in df_jvm_memory_usage['value']]
        df_jvm_memory_usage = df_jvm_memory_usage.set_index('time_series')
        df_jvm_memory_usage = df_jvm_memory_usage.resample('T').mean()

        df_request_count['time_series'] = pd.to_datetime(df_request_count['time_series'])
        request_count = df_request_count['value_success'] + df_request_count['value_fail']
        df_request_count['request_count'] = [self.req_flag(x) for x in request_count]
        df_request_count = df_request_count.set_index('time_series')
        df_request_count = df_request_count.resample('T').mean()

        df_response_time['time_series'] = pd.to_datetime(df_response_time['time_series'])
        df_response_time['response_time'] = [self.res_flag(x) for x in df_response_time['value']]
        df_response_time = df_response_time.set_index('time_series')
        df_response_time = df_response_time.resample('T').mean()

        df_final = df_cpu['cpu_usage'].to_frame()
        df_final = df_final.join(df_jvm_memory_usage['memory_usage'])
        df_final = df_final.join(df_response_time['response_time'])
        df_final = df_final.join(df_request_count['request_count'])

        #### Flag data
        df_final["health"] = 1 - ((df_final["cpu_usage"] + df_final["memory_usage"] + df_final["response_time"] + df_final["request_count"]) / 12)
        y = df_final["health"]

        return y

    def get_model(self, start_date, end_date):
        """Cria o modelo de Machine Learning para a previsão da saúde do sistema

        Args:
            start_date (String): Início do intervalo
            end_date (String): Fim do intervalo

        Returns:
            Machine Learning Model: Modelo de previsão da saúde do sistema
        """
        print("==========================================================================")
        ## dividir o dataset de treino e o dataset de teste
        y = self.get_data(start_date, end_date) #getting dataset for training

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

        #getting MSE RMSE
        start_date = datetime.datetime.strptime(
            start_date, '%Y-%m-%d %H:%M:%S')
        start_date = start_date.replace(second=0)
        start_date = start_date.strftime('%Y-%m-%d %H:%M:%S')

        end_date = datetime.datetime.strptime(
            end_date, '%Y-%m-%d %H:%M:%S')
        end_date = end_date.replace(second=0)
        end_date = end_date.strftime('%Y-%m-%d %H:%M:%S')

        pred, tempo_restante = self.get_predict(start_date, end_date)

        y_forecasted = pred.predicted_mean
        y_truth = teste.squeeze()
        mse = ((y_forecasted - y_truth) ** 2).mean()

        print('The Mean Squared Error of our forecasts is {}'.format(mse))

        print('The Root Mean Squared Error of our forecasts is {}'.format(np.sqrt(mse)))

        print("==========================================================================")

        return results

    def get_predict(self, start_date, end_date):
        """Gera previsão para uma nova série temporal

        Args:
            start_date (String): Início do intervalo
            end_date (String): Fim do intervalo

        Returns:
            PredictionResults instance: Objeto com os resultados da previsão
            int: Tempo em segundos até a próxima falha
        """
        print("Gerando previsão")

        pred = self.model.get_prediction(start=pd.to_datetime(
            start_date), end=pd.to_datetime(end_date))

        tempo_restante = self.get_time_to_event(start_date, pred)

        return pred, tempo_restante

    def get_time_to_event(self, date_now, pred):
        """Busca o próximo evento em que a previsão é igual ou menor 30%

        Args:
            date_now (String): Data e hora atual
            pred (PredictionResults instance): Objeto com os resultados da previsão

        Returns:
            int: Tempo restante em segundos até a próxima falha

        """
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
        """Função de testes para obetenção de contagem regressiva a partir de um timestamp

        Args:
            t (int): Contador em segundos
            tempo_restante (timedelta): Data e hora restante da contagem
        """
        print("Iniciando contagem até o evento")

        while t:
            tempo_restante = tempo_restante - datetime.timedelta(seconds=1)
            print(tempo_restante, end="\r")
            time.sleep(1)
            t -= 1
        print('A estabilidade do sistema está comprometida!')
        return

    def get_current_health(self):
        """Busca o último registro de cada collection;
           Aplica a flag de classificação de saúde do sistema; e
           Calcula saúde atual do sistema.

        Returns:
            float: Saúde atual do sistema
        """
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
        """Obtém a saúde atual do sistema;
           Gera previsão para uma nova série temporal;
        
        Args:
            time_range (String): Valor de intervalo entre duas datas

        Returns:
            float: Saúde atual do sistema
            float: Previsão para saúde atual (médial para um minuto)
            int: Tempo restante em segundos até a próxima falha
        """
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