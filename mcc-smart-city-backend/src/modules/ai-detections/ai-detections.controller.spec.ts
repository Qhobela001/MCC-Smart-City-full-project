import { Test, TestingModule } from '@nestjs/testing';
import { AiDetectionsController } from './ai-detections.controller';

describe('AiDetectionsController', () => {
  let controller: AiDetectionsController;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [AiDetectionsController],
    }).compile();

    controller = module.get<AiDetectionsController>(AiDetectionsController);
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });
});
