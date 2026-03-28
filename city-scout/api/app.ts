import express from 'express';
import cors from 'cors';
import { json } from 'express';
import { uploadRouter } from './routes/upload.js';
import { conversionRouter } from './routes/conversion.js';
import { analysisRouter } from './routes/analysis.js';
import { locationRouter } from './routes/location.js';
import { osmRouter } from './routes/osm.js';

const app = express();

app.use(cors());
app.use(json());

app.use('/api/upload', uploadRouter);
app.use('/api/convert', conversionRouter);
app.use('/api/analysis', analysisRouter);
app.use('/api/location', locationRouter);
app.use('/api/osm', osmRouter);

export default app;
