FROM ubuntu:22.04

LABEL maintainer="ENCODE DCC"
LABEL description="ENCODE Hi-C Pipeline: BWA + pairtools + Juicer + cooler"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl gzip pigz \
    python3 python3-pip \
    default-jre \
    libncurses5-dev libbz2-dev liblzma-dev zlib1g-dev libcurl4-openssl-dev \
    libhdf5-dev \
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

# pairtools 1.0.3
RUN pip3 install --no-cache-dir pairtools==1.0.3

# Juicer tools 2.20.00
RUN wget -q https://github.com/aidenlab/Juicebox/releases/download/v2.20.00/juicer_tools.2.20.00.jar \
    -O /opt/juicer_tools.jar

# cooler 0.9.3 + cooltools
RUN pip3 install --no-cache-dir cooler==0.9.3 cooltools==0.7.0

# FastQC 0.12.1
RUN wget -q https://www.bioinformatics.babraham.ac.uk/projects/fastqc/fastqc_v0.12.1.zip && \
    unzip -q fastqc_v0.12.1.zip -d /opt/ && chmod +x /opt/FastQC/fastqc && \
    ln -s /opt/FastQC/fastqc /usr/local/bin/ && rm fastqc_v0.12.1.zip

# MultiQC
RUN pip3 install --no-cache-dir multiqc==1.21

# Trim Galore
RUN pip3 install --no-cache-dir cutadapt==4.6 && \
    wget -q https://github.com/FelixKrueger/TrimGalore/archive/0.6.10.tar.gz && \
    tar xzf 0.6.10.tar.gz && ln -s /TrimGalore-0.6.10/trim_galore /usr/local/bin/ && \
    rm 0.6.10.tar.gz

WORKDIR /data
