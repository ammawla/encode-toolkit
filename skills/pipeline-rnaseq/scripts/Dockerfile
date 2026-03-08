# ENCODE RNA-seq Pipeline Docker Image
# STAR 2.7.10b, RSEM 1.3.3, Kallisto 0.48.0, RSeQC, samtools, Trim Galore, FastQC

FROM ubuntu:22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential wget curl git ca-certificates \
    zlib1g-dev libbz2-dev liblzma-dev libncurses5-dev libcurl4-openssl-dev \
    python3 python3-pip python3-dev default-jre \
    && rm -rf /var/lib/apt/lists/*

# STAR
RUN wget -qO- https://github.com/alexdobin/STAR/archive/refs/tags/2.7.10b.tar.gz | tar xz && \
    cp STAR-2.7.10b/bin/Linux_x86_64/STAR /usr/local/bin/ && \
    rm -rf STAR-2.7.10b

# RSEM
RUN wget -qO- https://github.com/deweylab/RSEM/archive/refs/tags/v1.3.3.tar.gz | tar xz && \
    cd RSEM-1.3.3 && make -j4 && make install && cd .. && rm -rf RSEM-1.3.3

# Kallisto
RUN wget -qO- https://github.com/pachterlab/kallisto/releases/download/v0.48.0/kallisto_linux-v0.48.0.tar.gz | tar xz && \
    cp kallisto/kallisto /usr/local/bin/ && rm -rf kallisto

# Samtools
RUN wget -qO- https://github.com/samtools/samtools/releases/download/1.17/samtools-1.17.tar.bz2 | tar xj && \
    cd samtools-1.17 && ./configure && make -j4 && make install && cd .. && rm -rf samtools-1.17

# bedGraphToBigWig
RUN wget -q http://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/bedGraphToBigWig -O /usr/local/bin/bedGraphToBigWig && \
    chmod +x /usr/local/bin/bedGraphToBigWig

# Python tools: RSeQC, MultiQC, Trim Galore (via cutadapt)
RUN pip3 install --no-cache-dir \
    RSeQC==4.0.0 multiqc==1.14 cutadapt==4.4

# Trim Galore
RUN wget -qO- https://github.com/FelixKrueger/TrimGalore/archive/refs/tags/0.6.7.tar.gz | tar xz && \
    cp TrimGalore-0.6.7/trim_galore /usr/local/bin/ && chmod +x /usr/local/bin/trim_galore && \
    rm -rf TrimGalore-0.6.7

# FastQC
RUN apt-get update && apt-get install -y --no-install-recommends fastqc && rm -rf /var/lib/apt/lists/*

WORKDIR /data
CMD ["/bin/bash"]
