import { Test, TestingModule } from '@nestjs/testing';
import { SystemHealthController } from './system-health.controller';

describe('SystemHealthController', () => {
  let controller: SystemHealthController;

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [SystemHealthController],
    }).compile();

    controller = module.get<SystemHealthController>(SystemHealthController);
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });
});
