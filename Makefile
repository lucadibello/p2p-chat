PROTO_FILES = ./proto/*.proto
OUTDIR = ./gen
PROTOC = protoc
CONDA_ENV = environment.yml
ENV_NAME = p2p

all: generate

$(OUTDIR):
	mkdir -p $(OUTDIR)

generate: $(OUTDIR)
	$(PROTOC) --python_out=$(OUTDIR) --pyi_out=$(OUTDIR) $(PROTO_FILES)

clean:
	rm -rf $(OUTDIR)

export-env:
	conda env export --no-builds > $(CONDA_ENV)

create-env:
	conda env create -f $(CONDA_ENV) -n $(ENV_NAME)

.PHONY: all generate clean
