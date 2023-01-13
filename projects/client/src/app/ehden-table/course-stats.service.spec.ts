import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { CourseStatsService } from './course-stats.service';

describe('CourseStatsService', () => {
  let service: CourseStatsService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [
        HttpClientTestingModule,
      ]
    });
    service = TestBed.inject(CourseStatsService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
