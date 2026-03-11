FROM ubuntu:22.04

LABEL maintainer="ENCODE DCC"
LABEL description="ENCODE DNase-seq Pipeline: BWA + Hotspot2 + HINT-ATAC"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl gzip pigz unzip \
    python3 python3-pip python3-dev \
    default-jre \
    libncurses5-dev libbz2-dev liblzma-dev zlib1g-dev libcurl4-openssl-dev \
    build-essential \
    bedops \
    && rm -rf /var/lib/apt/lists/*

# samtools 1.19
RUN wget -q https://github.com/samtools/samtools/releases/download/1.19/samtools-1.19.tar.bz2 && \
    tar xjf samtools-1.19.tar.bz2 && cd samtools-1.19 && \
    ./configure --prefix=/usr/local && make -j4 && make install && \
    cd .. && rm -rf samtools-1.19*

# BWA 0.7.17
RUN wget -q https://github.com/lh3/bwa/releases/download/v0.7.17/bwa-0.7.17.tar.bz2 && \
    tar xjf bwa-0.7.17.tar.bz2 && cd bwa-0.7.17 && \
    make -j4 && cp bwa /usr/local/bin/ && \
    cd .. && rm -rf bwa-0.7.17*

# bedtools 2.31.0
RUN wget -q https://github.com/arq5x/bedtools2/releases/download/v2.31.0/bedtools-2.31.0.tar.gz && \
    tar xzf bedtools-2.31.0.tar.gz && cd bedtools2 && \
    make -j4 && cp bin/* /usr/local/bin/ && \
    cd .. && rm -rf bedtools2 bedtools-2.31.0.tar.gz

# UCSC Kent tools (bedGraphToBigWig)
RUN wget -q https://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/bedGraphToBigWig \
    -O /usr/local/bin/bedGraphToBigWig && chmod +x /usr/local/bin/bedGraphToBigWig

# Hotspot2
RUN wget -q https://github.com/Altius/hotspot2/archive/refs/tags/v2.3.1.tar.gz && \
    tar xzf v2.3.1.tar.gz && cd hotspot2-2.3.1 && \
    make -j4 && cp hotspot2.sh scripts/* /usr/local/bin/ && \
    cd .. && rm -rf hotspot2-2.3.1 v2.3.1.tar.gz

# Picard 3.1.1
RUN wget -q https://github.com/broadinstitute/picard/releases/download/3.1.1/picard.jar \
    -O /opt/picard.jar && \
    echo '#!/bin/bash\njava -jar /opt/picard.jar "$@"' > /usr/local/bin/picard && \
    chmod +x /usr/local/bin/picard

# Trim Galore + cutadapt
RUN pip3 install --no-cache-dir cutadapt==4.6 && \
    wget -q https://github.com/FelixKrueger/TrimGalore/archive/0.6.10.tar.gz && \
    tar xzf 0.6.10.tar.gz && ln -s /TrimGalore-0.6.10/trim_galore /usr/local/bin/ && \
    rm 0.6.10.tar.gz

# HINT-ATAC (RGT)
RUN pip3 install --no-cache-dir RGT==0.13.2

# FastQC + MultiQC
RUN wget -q https://www.bioinformatics.babraham.ac.uk/projects/fastqc/fastqc_v0.12.1.zip && \
    unzip -q fastqc_v0.12.1.zip -d /opt/ && chmod +x /opt/FastQC/fastqc && \
    ln -s /opt/FastQC/fastqc /usr/local/bin/ && rm fastqc_v0.12.1.zip

RUN pip3 install --no-cache-dir multiqc==1.21

WORKDIR /data
