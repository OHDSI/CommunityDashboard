import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { StudyLeadsService } from './study-leads.service';

describe('StudyLeadsService', () => {
  let service: StudyLeadsService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [
        HttpClientTestingModule,
      ]
    });
    service = TestBed.inject(StudyLeadsService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
