import { Module } from '@nestjs/common';
import { UsersModule } from './modules/users/users.module';
import { RolesModule } from './modules/roles/roles.module';
import { DevicesModule } from './modules/devices/devices.module';
import { IncidentsModule } from './modules/incidents/incidents.module';
import { AiDetectionsModule } from './modules/ai-detections/ai-detections.module';
import { AnalyticsModule } from './modules/analytics/analytics.module';
import { NotificationsModule } from './modules/notifications/notifications.module';
import { SystemHealthModule } from './modules/system-health/system-health.module';
import { CamerasModule } from './modules/cameras/cameras.module';

@Module({
  imports: [UsersModule,
            RolesModule,
            DevicesModule,
            IncidentsModule,
            AiDetectionsModule,
            AnalyticsModule,
            NotificationsModule,
            SystemHealthModule,
            CamerasModule
          ],
})
export class AppModule {}
