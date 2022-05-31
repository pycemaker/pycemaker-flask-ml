from flask_restful import Api

from .controllers.predict import DoModelTraining, RegisterModelTraining, RemoveJob, ReturnPredictedData, ReturnHealth


def create_routes(api: Api):

    api.add_resource(RegisterModelTraining, '/register_training/<time_range>')
    api.add_resource(DoModelTraining, '/train_model/<time_range>')
    api.add_resource(ReturnPredictedData, '/predicted_data/<time_range>')
    api.add_resource(ReturnHealth, '/current_health/<time_range>')
    api.add_resource(RemoveJob, '/remove_training_job')
