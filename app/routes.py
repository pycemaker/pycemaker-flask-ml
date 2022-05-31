from flask_restful import Api

from .controllers.predict import DoModelTraining, RegisterModelTraining, RemoveJob, ReturnPredictedData, ReturnHealth


def create_routes(api: Api):

    api.add_resource(RegisterModelTraining, '/register_training')
    api.add_resource(DoModelTraining, '/train_model')
    api.add_resource(ReturnPredictedData, '/predicted_data')
    api.add_resource(ReturnHealth, '/current_health')
    api.add_resource(RemoveJob, '/remove_training_job')
