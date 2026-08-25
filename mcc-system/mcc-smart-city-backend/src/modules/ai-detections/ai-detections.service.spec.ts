import { Test, TestingModule } from '@nestjs/testing';
import { AiDetectionsService } from './ai-detections.service';

describe('AiDetectionsService', () => {
  let service: AiDetectionsService;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      providers: [AiDetectionsService],
    }).compile();

    service = module.get<AiDetectionsService>(AiDetectionsService);
  });

  it('should be defined', () => {
    expect(service).toBeDefined();
  });
});
