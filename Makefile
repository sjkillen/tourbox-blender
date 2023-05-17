all: addon.zip

.PHONY: target/release/tbelite
target/release/tbelite:
	cargo build --release

.PHONY: addon.zip
addon.zip: target/release/tbelite
	rm -rf /tmp/tourbox_addon
	cp -a tourbox_addon /tmp/tourbox_addon
	cp $^ /tmp/tourbox_addon
	rm -rf /tmp/tourbox_addon/__pycache__
	cd /tmp && rm -f addon.zip && zip -r addon.zip tourbox_addon/
	mv /tmp/addon.zip $@

.PHONY: clean
clean:
	rm -f addon.zip
	rm -rf addon/__pycache__
	cargo clean
