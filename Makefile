PROTO_FILES = ./proto/*.proto
OUTDIR = ./gen
PROTOC = protoc

all: generate

$(OUTDIR):
	mkdir -p $(OUTDIR)

generate: $(OUTDIR)
	$(PROTOC) --python_out=$(OUTDIR) --pyi_out=$(OUTDIR) $(PROTO_FILES)

clean:
	rm -rf $(OUTDIR)

.PHONY: all generate clean
