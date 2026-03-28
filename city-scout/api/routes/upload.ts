import { Router } from 'express';

const router = Router();

router.post('/terrain', (_req, res) => {
  res.json({ upload_id: 'mock-id-123', status: 'success' });
});

export { router as uploadRouter };
