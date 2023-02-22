import { HttpClientTestingModule } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { RepoSummariesService } from './repo-summaries.service';

describe('ReadmeSummariesService', () => {
  let service: RepoSummariesService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [
        HttpClientTestingModule,
      ]
    });
    service = TestBed.inject(RepoSummariesService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
