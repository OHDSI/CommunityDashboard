import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { StudyPipelineService } from './study-pipeline.service';

describe('StudyPipelineService', () => {
  let service: StudyPipelineService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [
        HttpClientTestingModule,
      ]
    });
    service = TestBed.inject(StudyPipelineService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
