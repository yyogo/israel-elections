# Deploy the static dashboard

Upload the **contents** of `dist/deployable-site.zip` to a static web host. Its
`index.html` is at the ZIP root. Do not upload the source takeout ZIP as a website.

Framework: static HTML / none. Build command: none. Publish directory: the extracted
site directory. No server, database, credentials or runtime environment variables.

All analysis data and ECharts 5.6.0 are embedded. Party-logo images remain remote;
missing logos do not remove party names or ballot letters. Preserve the included licenses.

To rebuild after editing source/data, run the three scripts in the root README.
The Site deployment attempted during this work was not created because Sites was
not enabled for the workspace. This archive has no hosting binding or Site project ID.
