# ENCODE ATAC-seq Pipeline Docker Image
# Multi-stage build for minimal final image

FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential wget curl git ca-certificates \
    zlib1g-dev libbz2-dev liblzma-dev libncurses5-dev libcurl4-openssl-dev \
    python3 python3-pip python3-dev default-jre \
    && rm -rf /var/lib/apt/lists/*

# Install Python tools
RUN pip3 install --no-cache-dir \
    macs2==2.2.9.1 idr==2.0.4.2 multiqc==1.14 cutadapt==4.4 \
    deeptools==3.5.4

# Bowtie2
RUN wget -qO- https://github.com/BenLangmead/bowtie2/releases/download/v2.5.1/bowtie2-2.5.1-linux-x86_64.zip > bowtie2.zip && \
    unzip bowtie2.zip && cp bowtie2-2.5.1-linux-x86_64/bowtie2* /usr/local/bin/ && \
    rm -rf bowtie2*

# Samtools
RUN wget -qO- https://github.com/samtools/samtools/releases/download/1.17/samtools-1.17.tar.bz2 | tar xj && \
    cd samtools-1.17 && ./configure && make -j4 && make install

# bedtools
RUN wget -qO- https://github.com/arq5x/bedtools2/releases/download/v2.31.0/bedtools-2.31.0.tar.gz | tar xz && \
    cd bedtools2 && make -j4 && cp bin/bedtools /usr/local/bin/

# Picard
RUN wget -qO /usr/local/bin/picard.jar https://github.com/broadinstitute/picard/releases/download/2.27.5/picard.jar && \
    echo '#!/bin/bash\njava -jar /usr/local/bin/picard.jar "$@"' > /usr/local/bin/picard && chmod +x /usr/local/bin/picard

# Trim Galore and FastQC
RUN apt-get update && apt-get install -y --no-install-recommends fastqc && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir trim-galore==0.6.7

# ataqv (ATAC-seq QC)
RUN wget -qO- https://github.com/ParkerLab/ataqv/releases/download/1.3.1/ataqv-1.3.1.tar.gz | tar xz && \
    cd ataqv-1.3.1 && make && cp bin/ataqv /usr/local/bin/ && cp bin/mkarv /usr/local/bin/

# bedGraphToBigWig
RUN wget -q http://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/bedGraphToBigWig -O /usr/local/bin/bedGraphToBigWig && \
    chmod +x /usr/local/bin/bedGraphToBigWig

WORKDIR /data
CMD ["/bin/bash"]
