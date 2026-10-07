# westfab-previews/

Westfab product preview renders: Blender, headless, one PNG per colour.

```bash
westfab-previews/render_preview.sh westfab-previews/layouts/WF-GF-4X4.json    # -> westfab-previews/output/WF-GF-4X4_{white,gray,black}_preview.png
```

| File | What |
|------|------|
| `render_preview.sh` | Renders a layout in each colour (default white, gray, black). |
| `render_layout.py` | The Blender script. Camera, lights, PLA material and background are fixed here so every preview looks the same. |
| `layouts/*.json` | Which bin STLs sit where on which baseplate. The only thing you normally edit. |

**Name each layout after the product's SKU** in the `company-os` vault —
`layouts/WF-GF-4X4.json` renders `1_Products/WF-GF-4X4.md`. For a product with
colour variants, use the parent SKU; the colours come from `--color`.

Options, the layout JSON format and how to generate the STLs it references are
in [`../westfab-instructions.md`](../westfab-instructions.md), section 2.

## Where the renders go next

`westfab-previews/output/` is gitignored and overwritten on every run. It is not where product
images live. After rendering, the PNGs are copied to OneDrive as masters,
converted to JPEG under the product's SKU, and uploaded to Cloudflare R2, where
they are served as `https://westfab.ro/img/products/<SKU>-<n>.jpg`.

That part of the flow is documented in the `company-os` vault:
`~/workspace/company-os/1_Products/_docs/Product images.md`.

**A layout change is a product change.** The bin list in the layout must match
the product's specs in the vault (`1_Products/<SKU>.md`), and the live image
only changes after the upload step. Update both together.
