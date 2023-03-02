import { TestBed } from '@angular/core/testing';

import { StudyTimelineService } from './study-timeline.service';

describe('StudyTimelineService', () => {
  let service: StudyTimelineService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(StudyTimelineService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
