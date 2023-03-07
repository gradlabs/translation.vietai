FROM mambaorg/micromamba:focal
COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml && \
    micromamba clean --all --yes

RUN mkdir /home/$MAMBA_USER/app
RUN chown $MAMBA_USER:$MAMBA_USER /home/$MAMBA_USER/app
WORKDIR /home/$MAMBA_USER/app
COPY --chown=$MAMBA_USER:$MAMBA_USER . .
RUN chmod +x entry.sh

CMD ["/bin/bash", "-c", "./entry.sh"]
