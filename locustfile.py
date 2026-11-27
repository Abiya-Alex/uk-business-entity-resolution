from locust import HttpUser, task, between

class BusinessUser(HttpUser):
    wait_time = between(0.5, 2)
    @task
    def search(self):
        self.client.get('/business',params={'name':'ABC','postcode':'TN9 1AB'})
