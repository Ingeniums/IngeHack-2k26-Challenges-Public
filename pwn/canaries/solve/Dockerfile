
FROM redpwn/jail

COPY --from=ubuntu / /srv


RUN mkdir -p /srv/app
COPY canaries /srv/app/canaries
COPY run.sh /srv/app/run
RUN chmod +x /srv/app/run
RUN chmod +x /srv/app/canaries

ENV JAIL_TIME=600