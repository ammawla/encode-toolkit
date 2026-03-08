FROM ubuntu:22.04

LABEL maintainer="ENCODE DCC"
LABEL description="ENCODE WGBS Pipeline: Bismark + MethylDackel"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget curl unzip gzip pigz \
    python3 python3-pip \
    default-jre \
    libncurses5-dev libbz2-dev liblzma-dev zlib1g-dev libcurl4-openssl-dev \
    && rm -rf /var/lib/apt/lists/*

# samtools 1.19
RUN wget -q https://github.com/samtools/samtools/releases/download/1.19/samtools-1.19.tar.bz2 && \
    tar xjf samtools-1.19.tar.bz2 && cd samtools-1.19 && \
    ./configure --prefix=/usr/local && make -j4 && make install && \
    cd .. && rm -rf samtools-1.19*

# htslib (tabix, bgzip) 1.19
RUN wget -q https://github.com/samtools/htslib/releases/download/1.19/htslib-1.19.tar.bz2 && \
    tar xjf htslib-1.19.tar.bz2 && cd htslib-1.19 && \
    ./configure --prefix=/usr/local && make -j4 && make install && \
    cd .. && rm -rf htslib-1.19*

# Bowtie2 2.5.3
RUN wget -q https://github.com/BenLangmead/bowtie2/releases/download/v2.5.3/bowtie2-2.5.3-linux-x86_64.zip && \
    unzip -q bowtie2-2.5.3-linux-x86_64.zip -d /opt/ && \
    ln -s /opt/bowtie2-2.5.3-linux-x86_64/bowtie2* /usr/local/bin/ && \
    rm bowtie2-2.5.3-linux-x86_64.zip

# Bismark 0.24.2
RUN wget -q https://github.com/FelixKrueger/Bismark/archive/v0.24.2.tar.gz && \
    tar xzf v0.24.2.tar.gz && mv Bismark-0.24.2 /opt/bismark && \
    ln -s /opt/bismark/bismark /usr/local/bin/ && \
    ln -s /opt/bismark/deduplicate_bismark /usr/local/bin/ && \
    ln -s /opt/bismark/bismark_genome_preparation /usr/local/bin/ && \
    rm v0.24.2.tar.gz

# Trim Galore 0.6.10
RUN pip3 install --no-cache-dir cutadapt==4.6 && \
    wget -q https://github.com/FelixKrueger/TrimGalore/archive/0.6.10.tar.gz && \
    tar xzf 0.6.10.tar.gz && ln -s /TrimGalore-0.6.10/trim_galore /usr/local/bin/ && \
    rm 0.6.10.tar.gz

# MethylDackel 0.6.1
RUN wget -q https://github.com/dpryan79/MethylDackel/archive/0.6.1.tar.gz && \
    tar xzf 0.6.1.tar.gz && cd MethylDackel-0.6.1 && \
    make CFLAGS="-O3 -Wall" && cp MethylDackel /usr/local/bin/ && \
    cd .. && rm -rf MethylDackel-0.6.1*

# FastQC 0.12.1
RUN wget -q https://www.bioinformatics.babraham.ac.uk/projects/fastqc/fastqc_v0.12.1.zip && \
    unzip -q fastqc_v0.12.1.zip -d /opt/ && chmod +x /opt/FastQC/fastqc && \
    ln -s /opt/FastQC/fastqc /usr/local/bin/ && rm fastqc_v0.12.1.zip

# MultiQC + Picard
RUN pip3 install --no-cache-dir multiqc==1.21

WORKDIR /data
