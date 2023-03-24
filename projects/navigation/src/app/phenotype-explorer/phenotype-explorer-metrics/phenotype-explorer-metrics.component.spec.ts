import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PhenotypeExplorerMetricsComponent } from './phenotype-explorer-metrics.component';

describe('PhenotypeExplorerMetricsComponent', () => {
  let component: PhenotypeExplorerMetricsComponent;
  let fixture: ComponentFixture<PhenotypeExplorerMetricsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ PhenotypeExplorerMetricsComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PhenotypeExplorerMetricsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
