import os
from apscheduler.schedulers.background import BackgroundScheduler
from models.specialite import SpecialiteModel


def start_ansm_scheduler(app):
    # Évite le double démarrage du scheduler avec le reloader Flask (mode debug)
    if app.debug and os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        return

    def job():
        with app.app_context():
            from utils.import_ansm import run_full_sync
            run_full_sync()

    scheduler = BackgroundScheduler(daemon=True, timezone='Europe/Paris')
    # La BDPM est mise à jour mensuellement par l'ANSM -> un run hebdo est largement suffisant
    scheduler.add_job(job, 'cron', day_of_week='sun', hour=3, id='ansm_resync', replace_existing=True)
    scheduler.start()
    print("📅 Scheduler ANSM démarré (resync chaque dimanche 3h)")

    # Bootstrap : si la base est vide (premier lancement), resync immédiate en tâche de fond
    with app.app_context():
        if SpecialiteModel.query.first() is None:
            print("⚠️ Référentiel ANSM vide, lancement d'une resync initiale en tâche de fond...")
            scheduler.add_job(job, id='ansm_bootstrap', replace_existing=True)