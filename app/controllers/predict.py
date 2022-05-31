import datetime
import json
from pyexpat import model
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


def call():
    response = requests.get("http://localhost:8080/train_model")
    response = response.json()
    print(response["msg"])


class RegisterModelTraining(Resource):

    def get(self) -> Response:
        job = scheduler.add_job(call, 'interval',
                                seconds=5, id="pycemaker-model")
        return jsonify("job details: %s" % (job))


class RemoveJob(Resource):

    def get(self) -> Response:
        scheduler.remove_job("pycemaker-model")
        return jsonify("%s foi encerrada" % ("pycemaker-model"))


class DoModelTraining(Resource):

    def get(self) -> Response:
        end_date = datetime.datetime.now()
        end_date = end_date + datetime.timedelta(hours=int(3))
        end_date = end_date.replace(second=0)
        end_date = end_date.replace(minute=0)
        start_date = end_date - datetime.timedelta(hours=int(3))
        start_date = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date = end_date.strftime('%Y-%m-%d %H:%M:%S')

        pcm_predict.get_model(start_date, end_date)
        # pcm_predict.get_model("2022-05-27 21:18:20", "2022-05-28 00:20:20")
        return jsonify({"msg": "Modelo treinado"})


class ReturnPredictedData(Resource):

    def get(self) -> Response:

        start_date = datetime.datetime.now()
        start_date = start_date.replace(second=0)
        start_date = start_date.replace(minute=0)
        start_date = start_date + datetime.timedelta(hours=int(3))
        end_date = start_date + datetime.timedelta(hours=int(3))
        start_date = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date = end_date.strftime('%Y-%m-%d %H:%M:%S')

        data, tempo_restante = pcm_predict.get_predict(start_date, end_date)
        # data, tempo_restante = pcm_predict.get_predict('2022-05-28 00:20:00', '2022-05-28 06:22:00')
        data = pd.DataFrame(data.predicted_mean)
        data = data.to_json(orient="table")
        data = json.loads(data)
        return jsonify({"remaining_time": tempo_restante, "data": data['data']})


class ReturnHealth(Resource):

    def get(self) -> Response:
        tempo_atual, tempo_previsao_atual, tempo_restante = pcm_predict.exec_current_health()
        return jsonify({
            "current_health": tempo_atual,
            "predicted_current_health": tempo_previsao_atual,
            "predicted_remaining_time": tempo_restante
        })
