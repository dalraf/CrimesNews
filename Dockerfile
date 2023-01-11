FROM python:3.10-slim

#Expose port 8080
EXPOSE 8080

RUN pip install poetry

#Copy all files in current directory into app directory
COPY . /app

#Change Working Directory to app directory
WORKDIR /app

#install all requirements in requirements.txt
RUN poetry export --without-hashes -f requirements.txt --output requirements.txt
RUN pip install -r requirements.txt

#Run the application on port 8080
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]