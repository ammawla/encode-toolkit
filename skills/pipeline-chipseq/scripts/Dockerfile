# ENCODE ChIP-seq Pipeline Docker Image
# Multi-stage build for minimal final image

FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential wget curl git ca-certificates \
    zlib1g-dev libbz2-dev liblzma-dev libncurses5-dev libcurl4-openssl-dev \
    python3 python3-pip python3-dev default-jre \
    && rm -rf /var/lib/apt/lists/*

# Install bioinformatics tools
RUN pip3 install --no-cache-dir \
    macs2==2.2.9.1 idr==2.0.4.2 multiqc==1.14 cutadapt==4.4

RUN wget -qO- https://github.com/lh3/bwa/releases/download/v0.7.17/bwa-0.7.17.tar.bz2 | tar xj && \
    cd bwa-0.7.17 && make && cp bwa /usr/local/bin/

RUN wget -qO- https://github.com/samtools/samtools/releases/download/1.17/samtools-1.17.tar.bz2 | tar xj && \
    cd samtools-1.17 && ./configure && make -j4 && make install

RUN wget -qO- https://github.com/arq5x/bedtools2/releases/download/v2.31.0/bedtools-2.31.0.tar.gz | tar xz && \
    cd bedtools2 && make -j4 && cp bin/bedtools /usr/local/bin/

RUN wget -qO- https://github.com/broadinstitute/picard/releases/download/2.27.5/picard.jar > /usr/local/bin/picard.jar && \
    echo '#!/bin/bash\njava -jar /usr/local/bin/picard.jar "$@"' > /usr/local/bin/picard && chmod +x /usr/local/bin/picard

RUN pip3 install --no-cache-dir trim-galore==0.6.7

RUN wget -qO /usr/local/bin/fastqc https://www.bioinformatics.babraham.ac.uk/projects/fastqc/fastqc_v0.11.9.zip || true
RUN apt-get update && apt-get install -y --no-install-recommends fastqc && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir deeptools==3.5.4

# phantompeakqualtools
RUN pip3 install --no-cache-dir phantompeakqualtools==1.2.2 || \
    (git clone https://github.com/kundajelab/phantompeakqualtools.git /opt/phantompeakqualtools && \
     chmod +x /opt/phantompeakqualtools/run_spp.R && \
     ln -s /opt/phantompeakqualtools/run_spp.R /usr/local/bin/run_spp.R)

# bedGraphToBigWig
RUN wget -q http://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/bedGraphToBigWig -O /usr/local/bin/bedGraphToBigWig && \
    chmod +x /usr/local/bin/bedGraphToBigWig

WORKDIR /data
CMD ["/bin/bash"]
