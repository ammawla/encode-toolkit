FROM ubuntu:22.04

LABEL maintainer="ENCODE DCC"
LABEL description="ENCODE CUT&RUN Pipeline: Bowtie2 + SEACR + MACS2 + deepTools"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl gzip pigz unzip \
    python3 python3-pip python3-dev \
    default-jre \
    libncurses5-dev libbz2-dev liblzma-dev zlib1g-dev libcurl4-openssl-dev \
    build-essential r-base \
    && rm -rf /var/lib/apt/lists/*

# samtools 1.19
RUN wget -q https://github.com/samtools/samtools/releases/download/1.19/samtools-1.19.tar.bz2 && \
    tar xjf samtools-1.19.tar.bz2 && cd samtools-1.19 && \
    ./configure --prefix=/usr/local && make -j4 && make install && \
    cd .. && rm -rf samtools-1.19*

# Bowtie2 2.5.3
RUN wget -q https://github.com/BenLangmead/bowtie2/releases/download/v2.5.3/bowtie2-2.5.3-linux-x86_64.zip && \
    unzip -q bowtie2-2.5.3-linux-x86_64.zip -d /opt/ && \
    ln -s /opt/bowtie2-2.5.3-linux-x86_64/bowtie2* /usr/local/bin/ && \
    rm bowtie2-2.5.3-linux-x86_64.zip

# bedtools 2.31.0
RUN wget -q https://github.com/arq5x/bedtools2/releases/download/v2.31.0/bedtools-2.31.0.tar.gz && \
    tar xzf bedtools-2.31.0.tar.gz && cd bedtools2 && \
    make -j4 && cp bin/* /usr/local/bin/ && \
    cd .. && rm -rf bedtools2 bedtools-2.31.0.tar.gz

# UCSC Kent tools
RUN wget -q https://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/bedGraphToBigWig \
    -O /usr/local/bin/bedGraphToBigWig && chmod +x /usr/local/bin/bedGraphToBigWig

# Picard 3.1.1
RUN wget -q https://github.com/broadinstitute/picard/releases/download/3.1.1/picard.jar \
    -O /opt/picard.jar && \
    echo '#!/bin/bash\njava -jar /opt/picard.jar "$@"' > /usr/local/bin/picard && \
    chmod +x /usr/local/bin/picard

# SEACR 1.3
RUN wget -q https://github.com/FredHutch/SEACR/archive/refs/tags/v1.3.tar.gz && \
    tar xzf v1.3.tar.gz && mv SEACR-1.3 /opt/SEACR && \
    ln -s /opt/SEACR/SEACR_1.3.sh /usr/local/bin/ && \
    rm v1.3.tar.gz

# MACS2 + deepTools + cutadapt
RUN pip3 install --no-cache-dir \
    macs2==2.2.9.1 \
    deeptools==3.5.4 \
    cutadapt==4.6

# Trim Galore
RUN wget -q https://github.com/FelixKrueger/TrimGalore/archive/0.6.10.tar.gz && \
    tar xzf 0.6.10.tar.gz && ln -s /TrimGalore-0.6.10/trim_galore /usr/local/bin/ && \
    rm 0.6.10.tar.gz

# FastQC + MultiQC
RUN wget -q https://www.bioinformatics.babraham.ac.uk/projects/fastqc/fastqc_v0.12.1.zip && \
    unzip -q fastqc_v0.12.1.zip -d /opt/ && chmod +x /opt/FastQC/fastqc && \
    ln -s /opt/FastQC/fastqc /usr/local/bin/ && rm fastqc_v0.12.1.zip

RUN pip3 install --no-cache-dir multiqc==1.21

WORKDIR /data
