# Use an official Python runtime as a parent image
FROM continuumio/miniconda3:24.1.2-0

# Set the working directory in the container to /app
WORKDIR /app

# Add current directory files to /app in the container
ADD . /app

# Clone the git repo
RUN git clone https://github.com/giorgialari/OpenVoiceV2_git.git

# Set the working directory to OpenVoice
WORKDIR /app/OpenVoiceV2_git

# Create a new conda environment with python 3.9 and activate it
RUN conda create -n openvoice python=3.9
RUN echo "source activate openvoice" > ~/.bashrc
ENV PATH /opt/conda/envs/openvoice/bin:$PATH
# force python to use unbuffered mode for logging
ENV PYTHONUNBUFFERED=1

# Install the OpenVoice package and uvicorn for FastAPI
# Install MeloTTS
RUN git clone https://github.com/myshell-ai/MeloTTS.git && \
  cd MeloTTS && \
  pip install -e . && \
  python -m unidic download && \
  cd ..

RUN pip install -e .
RUN pip install uvicorn ffmpeg
  
RUN pip install -r requirements.txt

# Download and extract the checkpoint file
RUN apt-get update && apt-get install -y unzip wget
RUN wget https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip
RUN unzip checkpoints_v2_0417.zip -d ./openvoice
RUN rm checkpoints_v2_0417.zip
# RUN mv resources openvoice/resources

# Make port 8000 available to the world outside this container
EXPOSE 8000
EXPOSE 7860

RUN cd /app/OpenVoiceV2_git/openvoice
WORKDIR /app/OpenVoiceV2_git/openvoice

RUN conda install ffmpeg
RUN conda install --yes libmagic

# copy the startup script into the container
COPY start.sh /app/OpenVoiceV2_git/openvoice/start.sh

# Provide permissions to execute the script
RUN chmod +x /app/OpenVoiceV2_git/openvoice/start.sh

# Start the server once to initiate the first time setup that downloads some models.
COPY start_and_stop_server.sh /app/OpenVoiceV2_git/start_and_stop_server.sh
RUN chmod +x /app/OpenVoiceV2_git/start_and_stop_server.sh
RUN /app/OpenVoiceV2_git/start_and_stop_server.sh

# Run the startup script which installs libmagic and starts the server, when the container launches
CMD ["bash", "/app/OpenVoiceV2_git/start.sh"]
