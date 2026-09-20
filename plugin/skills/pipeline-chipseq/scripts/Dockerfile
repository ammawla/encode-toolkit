# ENCODE ChIP-seq Pipeline Docker Image
# Multi-stage build for minimal final image

FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
# perl is listed explicitly: FastQC and Trim Galore are Perl programs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential wget curl git ca-certificates perl \
    zlib1g-dev libbz2-dev liblzma-dev libncurses5-dev libcurl4-openssl-dev \
    python3 python3-pip python3-dev default-jre \
    && rm -rf /var/lib/apt/lists/*

# Install bioinformatics tools
RUN pip3 install --no-cache-dir \
    numpy==1.23.5 macs2==2.2.9.1 multiqc==1.14 cutadapt==4.4

# IDR 2.0.4.2 is not on PyPI (the PyPI package named idr is unrelated). Install the release
# ENCODE uses from its GitHub tag. It imports numpy in setup.py and uses numpy.int at
# runtime, so numpy is installed first and held below 1.24.
RUN pip3 install --no-cache-dir --no-build-isolation \
    https://github.com/kundajelab/idr/archive/refs/tags/2.0.4.2.tar.gz

RUN wget -qO- https://github.com/lh3/bwa/archive/refs/tags/v0.7.18.tar.gz | tar xz && \
    cd bwa-0.7.18 && make && cp bwa /usr/local/bin/

RUN wget -qO- https://github.com/samtools/samtools/releases/download/1.17/samtools-1.17.tar.bz2 | tar xj && \
    cd samtools-1.17 && ./configure && make -j4 && make install

RUN wget -qO- https://github.com/arq5x/bedtools2/releases/download/v2.31.0/bedtools-2.31.0.tar.gz | tar xz && \
    cd bedtools2 && make -j4 && cp bin/bedtools /usr/local/bin/

RUN wget -qO- https://github.com/broadinstitute/picard/releases/download/2.27.5/picard.jar > /usr/local/bin/picard.jar && \
    echo '#!/bin/bash\njava -jar /usr/local/bin/picard.jar "$@"' > /usr/local/bin/picard && chmod +x /usr/local/bin/picard

# Trim Galore is a Perl script and is not published on PyPI; install the tagged release
RUN wget -qO- https://github.com/FelixKrueger/TrimGalore/archive/refs/tags/0.6.7.tar.gz | tar xz && \
    cp TrimGalore-0.6.7/trim_galore /usr/local/bin/ && chmod +x /usr/local/bin/trim_galore && \
    rm -rf TrimGalore-0.6.7

RUN apt-get update && apt-get install -y --no-install-recommends fastqc && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir deeptools==3.5.5

# bedGraphToBigWig
RUN wget -q https://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/bedGraphToBigWig -O /usr/local/bin/bedGraphToBigWig && \
    chmod +x /usr/local/bin/bedGraphToBigWig

WORKDIR /data
CMD ["/bin/bash"]
