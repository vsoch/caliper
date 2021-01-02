FROM {{ base }}
ADD . /tmp/repo
WORKDIR /tmp/repo
ENV LANG C.UTF-8
ENV SHELL /bin/bash
RUN apt-get update && apt-get install -y wget ca-certificates gnupg2 git
RUN /bin/bash -c "wget {{ filename }} && pip install {{ basename }}"
{% if deps %}RUN pip install {{ deps }}{% endif %}
