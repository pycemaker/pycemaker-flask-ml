import datetime
import json
from flask import Response, jsonify
from flask_restful import Resource
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from pymongo import MongoClient
import requests
import os
import pandas as pd

from app.services.pycemaker import PcmPredict

mongo = MongoClient(os.environ.get("MONGO_DB_URL"))

jobstores = {
    'default': MongoDBJobStore(database="pycemaker", client=mongo, collection="training_jobs")
}

scheduler = BackgroundScheduler(jobstores=jobstores)
scheduler.start()

pcm_predict = PcmPredict()


def call(time_range):
    response = requests.get("%s/train_model/%s" %
                            (os.environ.get("ML_URL"), time_range))
    response = response.json()
    print(response["msg"])


class RegisterModelTraining(Resource):

    def get(self, time_range) -> Response:
        job = scheduler.add_job(call, 'interval',
                                hours=int(time_range), next_run_time=datetime.datetime.now(), id="pycemaker-model", args=[time_range])
        return jsonify("job details: %s" % (job))


class RemoveJob(Resource):

    def get(self) -> Response:
        scheduler.remove_job("pycemaker-model")
        return jsonify("%s foi encerrada" % ("pycemaker-model"))


class DoModelTraining(Resource):

    def get(self, time_range) -> Response:
        end_date = datetime.datetime.now()
        end_date = end_date + datetime.timedelta(hours=int(3))
        end_date = end_date.replace(second=0)
        end_date = end_date.replace(minute=0)
        start_date = end_date - datetime.timedelta(hours=int(time_range))
        start_date = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date = end_date.strftime('%Y-%m-%d %H:%M:%S')

        pcm_predict.get_model(start_date, end_date)
        # pcm_predict.get_model("2022-05-27 21:18:20", "2022-05-28 00:20:20")
        return jsonify({"msg": "Modelo treinado"})


class ReturnPredictedData(Resource):

    def get(self, time_range) -> Response:

        start_date = datetime.datetime.now()
        start_date = start_date.replace(second=0)
        start_date = start_date.replace(minute=0)
        start_date = start_date + datetime.timedelta(hours=int(3))
        end_date = start_date + datetime.timedelta(hours=int(time_range))
        start_date = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date = end_date.strftime('%Y-%m-%d %H:%M:%S')

        data, tempo_restante = pcm_predict.get_predict(start_date, end_date)
        # data, tempo_restante = pcm_predict.get_predict('2022-05-28 00:20:00', '2022-05-28 06:22:00')
        data = pd.DataFrame(data.predicted_mean)
        data = data.to_json(orient="table")
        data = json.loads(data)
        return jsonify({"remaining_time": tempo_restante, "data": data['data']})


class ReturnHealthData(Resource):

    def get(self, time_range) -> Response:
        end_date = datetime.datetime.now()
        end_date = end_date + datetime.timedelta(hours=int(3))
        end_date = end_date.replace(second=0)
        end_date = end_date.replace(minute=0)
        start_date = end_date - datetime.timedelta(hours=int(time_range))
        start_date = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date = end_date.strftime('%Y-%m-%d %H:%M:%S')

        data = pcm_predict.get_data_for_train(start_date, end_date)
        # data = pd.DataFrame(data)
        data = data.to_json(orient="table")
        data = json.loads(data)

        return jsonify({"data": data['data']})


class ReturnHealth(Resource):

    def get(self, time_range) -> Response:
        print(time_range)
        tempo_atual, tempo_previsao_atual, tempo_restante = pcm_predict.exec_current_health(
            time_range)
        return jsonify({
            "current_health": tempo_atual,
            "predicted_current_health": tempo_previsao_atual,
            "predicted_remaining_time": tempo_restante
        })
