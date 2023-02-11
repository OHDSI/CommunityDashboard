import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { StudyExceptionsService } from './study-exceptions.service';

describe('StudyExceptionsService', () => {
  let service: StudyExceptionsService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [
        HttpClientTestingModule,
      ]
    });
    service = TestBed.inject(StudyExceptionsService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
