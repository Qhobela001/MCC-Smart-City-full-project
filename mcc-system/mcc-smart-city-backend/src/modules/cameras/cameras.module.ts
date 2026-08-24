import { Module } from '@nestjs/common';
import { CamerasService } from './cameras.service';

@Module({
  providers: [CamerasService]
})
export class CamerasModule {}
