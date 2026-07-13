import { Module } from '@nestjs/common';
import { AiDetectionsController } from './ai-detections.controller';
import { AiDetectionsService } from './ai-detections.service';

@Module({
  controllers: [AiDetectionsController],
  providers: [AiDetectionsService]
})
export class AiDetectionsModule {}
